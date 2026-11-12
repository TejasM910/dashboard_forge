"""Infers Primary Keys, Candidate Foreign Keys, Grain, and Joins across profiled tables (T-203)."""

from typing import List, Tuple
from pydantic import BaseModel, Field
from dforge.tools.profiling.profiler import TableProfile


class CandidateRelationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    join_type: str = "INNER JOIN"
    confidence: float = 1.0


class SchemaGraph(BaseModel):
    table_pks: dict[str, List[str]] = Field(default_factory=dict)
    relationships: List[CandidateRelationship] = Field(default_factory=list)


class RelationshipInferrer:
    """Infers keys and joins across tables based on naming conventions and statistics."""

    @staticmethod
    def infer_schema_graph(profiles: List[TableProfile]) -> SchemaGraph:
        table_pks: dict[str, List[str]] = {}
        for tp in profiles:
            pks = [c.name for c in tp.columns if c.is_candidate_pk]
            # Fallback heuristic: column ending with _id matching table name singular
            if not pks:
                expected_id = f"{tp.table_name.rstrip('s')}_id"
                pks = [c.name for c in tp.columns if c.name == expected_id]
            table_pks[tp.table_name] = pks

        relationships: List[CandidateRelationship] = []
        for tp in profiles:
            for col in tp.columns:
                # Look for foreign keys pointing to other tables
                if col.name.endswith("_id") and not col.is_candidate_pk:
                    target_table_candidate = col.name[:-3] + "s"  # customer_id -> customers
                    for other_tp in profiles:
                        if other_tp.table_name == target_table_candidate:
                            target_pk = table_pks.get(other_tp.table_name, [])
                            if col.name in target_pk or any(p == col.name for p in target_pk):
                                relationships.append(
                                    CandidateRelationship(
                                        from_table=tp.table_name,
                                        from_column=col.name,
                                        to_table=other_tp.table_name,
                                        to_column=col.name,
                                        join_type="JOIN",
                                        confidence=0.95,
                                    )
                                )

        return SchemaGraph(table_pks=table_pks, relationships=relationships)
