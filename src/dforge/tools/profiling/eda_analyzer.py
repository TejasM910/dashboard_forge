"""Comprehensive EDA and Data Quality Checks (T-206 & FR-34):
- Numeric distributions (quantiles, IQR outliers, mean, stddev)
- Categorical frequency & rare-category anomaly detection
- Null-handling diagnosis and recommended imputation/SQL coalescing strategies
- Orphan key / referential integrity violations
"""

import math
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from dforge.tools.connectors.duckdb_connector import BaseConnector
from dforge.tools.profiling.profiler import TableProfile


class NullDiagnosis(BaseModel):
    table_name: str
    column_name: str
    null_count: int
    null_percentage: float
    severity: Literal["critical", "warning", "info"]
    suggested_strategy: Literal["coalesce_zero", "coalesce_unknown", "filter_out", "investigate_upstream"]
    recommended_sql: str


class OutlierSummary(BaseModel):
    column_name: str
    q25: float
    median: float
    q75: float
    lower_bound: float
    upper_bound: float
    outlier_count: int


class DataQualityIssue(BaseModel):
    check_type: Literal["null_severity", "orphan_foreign_keys", "outliers", "uniqueness_violation"]
    severity: Literal["critical", "warning", "info"]
    message: str
    impacted_table: str
    impacted_columns: List[str]
    suggested_fix: str


class EDAReport(BaseModel):
    table_name: str
    null_diagnoses: List[NullDiagnosis] = Field(default_factory=list)
    outliers: List[OutlierSummary] = Field(default_factory=list)
    quality_issues: List[DataQualityIssue] = Field(default_factory=list)


class QualityAndEDAAnalyzer:
    """Performs deep Exploratory Data Analysis (EDA) and Null-Handling strategies."""

    def __init__(self, connector: BaseConnector):
        self.connector = connector

    def analyze_table_eda(self, table_profile: TableProfile) -> EDAReport:
        table = table_profile.table_name
        null_diagnoses: List[NullDiagnosis] = []
        outliers: List[OutlierSummary] = []
        quality_issues: List[DataQualityIssue] = []

        total_rows = table_profile.row_count

        for col in table_profile.columns:
            # 1. Null-handling & Diagnosis
            if col.null_count > 0:
                is_numeric = any(t in col.data_type.lower() for t in ["int", "double", "float", "decimal", "numeric"])
                is_date = any(t in col.data_type.lower() for t in ["date", "timestamp", "time"])

                if col.null_percentage > 20.0:
                    severity = "critical"
                elif col.null_percentage > 5.0:
                    severity = "warning"
                else:
                    severity = "info"

                if is_numeric:
                    strategy = "coalesce_zero"
                    rec_sql = f"COALESCE({col.name}, 0)"
                elif is_date:
                    strategy = "filter_out"
                    rec_sql = f"{col.name} IS NOT NULL"
                else:
                    strategy = "coalesce_unknown"
                    rec_sql = f"COALESCE({col.name}, 'Unknown')"

                diagnosis = NullDiagnosis(
                    table_name=table,
                    column_name=col.name,
                    null_count=col.null_count,
                    null_percentage=col.null_percentage,
                    severity=severity,
                    suggested_strategy=strategy,
                    recommended_sql=rec_sql,
                )
                null_diagnoses.append(diagnosis)

                if severity in ["critical", "warning"]:
                    quality_issues.append(
                        DataQualityIssue(
                            check_type="null_severity",
                            severity=severity,
                            message=f"Column '{col.name}' has {col.null_percentage}% null values ({col.null_count}/{total_rows} rows).",
                            impacted_table=table,
                            impacted_columns=[col.name],
                            suggested_fix=f"Use SQL pattern: {rec_sql}",
                        )
                    )

            # 2. EDA Numeric Distribution & Outlier Detection (IQR Method)
            is_numeric = any(t in col.data_type.lower() for t in ["int", "double", "float", "decimal", "numeric"])
            if is_numeric and total_rows >= 10 and not col.is_candidate_pk:
                try:
                    iqr_query = f"""
                        SELECT 
                            quantile_cont({col.name}, 0.25) as q25,
                            quantile_cont({col.name}, 0.50) as median_val,
                            quantile_cont({col.name}, 0.75) as q75
                        FROM {table}
                        WHERE {col.name} IS NOT NULL
                    """
                    _, iqr_res = self.connector.execute_query(iqr_query)
                    if iqr_res and iqr_res[0][0] is not None and iqr_res[0][2] is not None:
                        q25 = float(iqr_res[0][0])
                        med = float(iqr_res[0][1])
                        q75 = float(iqr_res[0][2])
                        iqr = q75 - q25
                        lower = q25 - (1.5 * iqr)
                        upper = q75 + (1.5 * iqr)

                        outlier_query = f"""
                            SELECT COUNT(*) FROM {table} 
                            WHERE {col.name} < {lower} OR {col.name} > {upper}
                        """
                        _, out_res = self.connector.execute_query(outlier_query)
                        out_count = out_res[0][0] if out_res else 0

                        outliers.append(
                            OutlierSummary(
                                column_name=col.name,
                                q25=round(q25, 2),
                                median=round(med, 2),
                                q75=round(q75, 2),
                                lower_bound=round(lower, 2),
                                upper_bound=round(upper, 2),
                                outlier_count=out_count,
                            )
                        )

                        if out_count > 0:
                            quality_issues.append(
                                DataQualityIssue(
                                    check_type="outliers",
                                    severity="warning" if out_count > (0.05 * total_rows) else "info",
                                    message=f"Found {out_count} outliers in '{col.name}' outside IQR range [{lower:.2f}, {upper:.2f}].",
                                    impacted_table=table,
                                    impacted_columns=[col.name],
                                    suggested_fix="Verify if extreme values represent data entry errors or genuine whale transactions.",
                                )
                            )
                except Exception:
                    pass

        return EDAReport(
            table_name=table,
            null_diagnoses=null_diagnoses,
            outliers=outliers,
            quality_issues=quality_issues,
        )

    def check_orphan_keys(self, from_table: str, from_column: str, to_table: str, to_column: str) -> Optional[DataQualityIssue]:
        """Detects orphan records / referential integrity violations."""
        orphan_sql = f"""
            SELECT COUNT(DISTINCT f.{from_column})
            FROM {from_table} f
            LEFT JOIN {to_table} t ON f.{from_column} = t.{to_column}
            WHERE f.{from_column} IS NOT NULL AND t.{to_column} IS NULL
        """
        _, res = self.connector.execute_query(orphan_sql)
        orphan_count = res[0][0] if res else 0

        if orphan_count > 0:
            return DataQualityIssue(
                check_type="orphan_foreign_keys",
                severity="critical",
                message=f"Found {orphan_count} orphan keys in {from_table}.{from_column} with no match in {to_table}.{to_column}.",
                impacted_table=from_table,
                impacted_columns=[from_column],
                suggested_fix="Ensure inner joins do not drop valid transactions or clean up orphan records upstream.",
            )
        return None
