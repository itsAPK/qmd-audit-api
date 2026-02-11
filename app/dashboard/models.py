# schemas/admin_dashboard.py
from pydantic import BaseModel
from typing import List, Dict


class LabelCount(BaseModel):
    label: str
    count: int


class LabelValue(BaseModel):
    label: str
    value: int | float


class DashboardStats(BaseModel):
    total_audits: int
    total_ncrs: int
    open_ncrs: int
    closed_ncrs: int
    overdue_ncrs: int
    edc_compliance_pct: float
    avg_closure_days: float
    rejection_rate_pct: float
    edc_extension_requests: int


class StatusDistribution(BaseModel):
    status: str
    count: int


class MonthlyTrend(BaseModel):
    month: str
    raised: int
    closed: int


class OverdueTrend(BaseModel):
    date: str
    count: int


class AgingBucket(BaseModel):
    bucket: str
    count: int


class OverviewGraphs(BaseModel):
    ncr_status_distribution: List[StatusDistribution]
    monthly_ncr_trend: List[MonthlyTrend]
    overdue_ncr_trend: List[OverdueTrend]
    plant_wise_ncrs: List[LabelCount]
    department_wise_ncrs: List[LabelCount]
    ncr_aging_buckets: List[AgingBucket]
    root_cause_distribution: List[LabelCount]


class AuditorWorkload(BaseModel):
    auditor: str
    assigned: int
    completed: int


class AuditeeCompliance(BaseModel):
    auditee: str
    closure_rate: float
    overdue_pct: float


class ExtraAdminGraphs(BaseModel):
    audit_type_ncrs: List[LabelValue]
    auditor_workload: List[AuditorWorkload]
    auditee_compliance: List[AuditeeCompliance]
    followup_cycles: List[LabelValue]
    edc_extension_trend: List[LabelValue]
    rejection_reasons: List[LabelValue]
    audit_vs_ncr_ratio: List[LabelValue]
    sla_buckets: List[LabelValue]
    repeat_ncrs: List[LabelValue]


# ---------- COMPARISON ----------
class PeriodCompare(BaseModel):
    previous: int
    current: int


class MonthComparison(BaseModel):
    raised: PeriodCompare
    closed: PeriodCompare


class PlantCompare(BaseModel):
    plant: str
    overdue_pct: float
    avg_closure_days: float


class DepartmentCompare(BaseModel):
    department: str
    overdue_pct: float
    avg_closure_days: float


class ComparisonGraphs(BaseModel):
    month_vs_last_month: MonthComparison
    plant_comparison: List[PlantCompare]
    department_comparison: List[DepartmentCompare]
    before_after_corrective_action: Dict[str, int]
    target_vs_actual: Dict[str, float | int]


class AdminDashboardResponse(BaseModel):
    stats: DashboardStats
    overview_graphs: OverviewGraphs
    extra_admin_graphs: ExtraAdminGraphs
    comparison_graphs: ComparisonGraphs



from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# =========================================================
# COMMON / SHARED SCHEMAS
# =========================================================

class StatusCount(BaseModel):
    status: str
    count: int


class LabelCount(BaseModel):
    label: str
    count: int


class NameCount(BaseModel):
    name: str
    count: int


class AgingBucket(BaseModel):
    bucket: str   # 0-7, 8-15, 16-30, 30+
    count: int


# =========================================================
# AUDIT / FOLLOW-UP RELATED
# =========================================================

class AuditDelayPoint(BaseModel):
    planned_end_date: datetime
    actual_end_date: Optional[datetime]


class AuditorWorkload(BaseModel):
    auditor: str
    audits_count: int
    ncrs_count: int


# =========================================================
# 🧑‍💼 HOD DASHBOARD SCHEMAS
# =========================================================

class HodStats(BaseModel):
    total_audits: int
    audits_completed: int
    audits_in_progress: int
    total_ncrs: int
    open_ncrs: int
    overdue_ncrs: int
    rejected_ncrs: int
    avg_ncr_closure_days: float


class HodCharts(BaseModel):
    audit_status_distribution: List[StatusCount]
    department_audit_coverage: List[NameCount]
    department_ncr_distribution: List[NameCount]
    ncr_status_distribution: List[StatusCount]
    ncr_aging: List[AgingBucket]
    edc_status_distribution: List[StatusCount]
    followup_effectiveness: List[LabelCount]
    auditor_workload: List[AuditorWorkload]
    clause_wise_ncrs: List[LabelCount]
    ncr_delay_trend: List[AuditDelayPoint]


class HodDashboardResponse(BaseModel):
    stats: HodStats
    charts: HodCharts



class AuditorStats(BaseModel):
    assigned_audits: int
    audits_completed: int
    ncrs_raised: int
    open_ncrs: int
    followups_assigned: int
    avg_closure_days: float


class MonthlyTrendPoint(BaseModel):
    month: str     # YYYY-MM
    count: int


class AuditorCharts(BaseModel):
    audit_status_distribution: List[StatusCount]
    ncr_monthly_trend: List[MonthlyTrendPoint]
    ncr_status_distribution: List[StatusCount]
    ncr_severity_mode: List[LabelCount]
    ncr_aging: List[AgingBucket]
    clause_wise_ncrs: List[LabelCount]
    followup_outcome: List[StatusCount]


class PendingEDCRow(BaseModel):
    edc_id: str
    ncr_id: str


class AuditorTables(BaseModel):
    pending_edc_reviews: List[PendingEDCRow]


class AuditorDashboardResponse(BaseModel):
    stats: AuditorStats
    charts: AuditorCharts
    tables: AuditorTables



class AuditeeStats(BaseModel):
    total_ncrs: int
    open_ncrs: int
    overdue_ncrs: int
    rejected_ncrs: int
    avg_closure_days: float


class LifecycleStage(BaseModel):
    stage: str
    count: int


class AuditeeCharts(BaseModel):
    ncr_lifecycle_funnel: List[LifecycleStage]
    corrective_action_delay: List[LabelCount]   # On Time / Delayed
    root_cause_distribution: List[LabelCount]
    edc_status_distribution: List[StatusCount]
    rejection_reasons: List[LabelCount]
    clause_wise_ncrs: List[LabelCount]


class AuditeeDashboardResponse(BaseModel):
    stats: AuditeeStats
    charts: AuditeeCharts


class DepartmentRiskRow(BaseModel):
    department: str
    total_ncr: int
    rejected: int
    overdue: int

class ClauseHeatmapRow(BaseModel):
    clause: str | None
    department: str
    count: int

class AuditStats(BaseModel):
    total_ncrs: int
    open_ncrs: int
    overdue_ncrs: int
    rejected_ncrs: int
    plant_risk_score: int


class AuditGraphs(BaseModel):
    department_risk: List[DepartmentRiskRow]
    clause_heatmap: List[ClauseHeatmapRow]
    edc_by_department: List[LabelCount]

class AuditDashboardResponse(BaseModel):
    stats: AuditStats
    graphs: AuditGraphs

class AuditInfoStats(BaseModel):
    total_ncrs: int
    open_ncrs: int
    closed_ncrs: int
    overdue_ncrs: int
    total_edc: int
    pending_edc: int
    total_followups: int

class AuditInfoCharts(BaseModel):
    ncr_status_distribution: List[StatusCount]
    edc_status_distribution: List[StatusCount]
    followup_status_distribution: List[StatusCount]
    ncr_aging: List[AgingBucket]
    root_cause_distribution: List[LabelCount]
    clause_distribution: List[LabelCount]

class AuditInfoDashboardResponse(BaseModel):
    stats: AuditInfoStats
    charts: AuditInfoCharts
