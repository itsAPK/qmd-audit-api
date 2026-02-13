from sqlalchemy import (
    select,
    func,
    case,
    text,
    Numeric,
    cast,
)
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.audit.models import Audit
from app.audit_info.models import AuditInfo, AuditInfoStatus, AuditTeam, AuditTeamRole
from app.edc_request.models import EDCStatus, EdcRequest
from app.followup.models import Followup
from app.ncr.models import NCR, NCRStatus, NCRTeam, NCRTeamRole
from app.settings.models import Department, Plant
from app.users.models import User


class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------
    # COMMON DATE FILTER
    # -------------------------------------------------
    def _date_filters(self, column, from_date, to_date):
        filters = []
        if from_date:
            filters.append(column >= from_date)
        if to_date:
            filters.append(column <= to_date)
        return filters

    # -------------------------------------------------
    # ADMIN DASHBOARD
    # -------------------------------------------------
    async def get_admin_dashboard(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):

        ncr_date_filters = self._date_filters(NCR.created_at, from_date, to_date)

        # =========================
        # STATS
        # =========================

        total_audits = await self.session.scalar(select(func.count(Audit.id)))

        total_ncrs = await self.session.scalar(
            select(func.count(NCR.id)).where(*ncr_date_filters)
        )

        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id)).where(
                NCR.status != NCRStatus.CLOSED, *ncr_date_filters
            )
        )

        closed_ncrs = await self.session.scalar(
            select(func.count(NCR.id)).where(
                NCR.status == NCRStatus.CLOSED, *ncr_date_filters
            )
        )

        overdue_ncrs = await self.session.scalar(
            select(func.count(NCR.id)).where(
                NCR.edc_given_date < func.now(),
                NCR.status != NCRStatus.CLOSED,
                *ncr_date_filters,
            )
        )

        raw_edc_compliance = await self.session.scalar(
            select(
                (
                    func.count(NCR.id).filter(
                        NCR.actual_date_of_completion <= NCR.edc_given_date
                    )
                    * 100.0
                    / func.nullif(func.count(NCR.id), 0)
                )
            ).where(NCR.status == NCRStatus.CLOSED, *ncr_date_filters)
        )

        edc_compliance_pct = round(raw_edc_compliance or 0, 2)

        raw_avg_days = await self.session.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        NCR.actual_date_of_completion - NCR.created_at,
                    )
                    / 86400
                )
            ).where(NCR.status == NCRStatus.CLOSED, *ncr_date_filters)
        )

        avg_closure_days = round(raw_avg_days or 0, 2)

        raw_rejection_rate = await self.session.scalar(
            select(
                func.sum(NCR.rejected_count)
                * 100.0
                / func.nullif(func.count(NCR.id), 0)
            ).where(*ncr_date_filters)
        )

        rejection_rate_pct = round(raw_rejection_rate or 0, 2)

        edc_extension_requests = await self.session.scalar(
            select(func.count(EdcRequest.id)).where(
                EdcRequest.status == EDCStatus.PENDING
            )
        )

        # =========================
        # OVERVIEW GRAPHS
        # =========================

        status_dist = (
            await self.session.execute(
                select(NCR.status, func.count(NCR.id))
                .where(*ncr_date_filters)
                .group_by(NCR.status)
            )
        ).all()

        month_expr = func.to_char(
            func.date_trunc("month", NCR.created_at), "YYYY-MM"
        ).label("month")

        monthly_trend = (
            await self.session.execute(
                select(
                    month_expr,
                    func.count(NCR.id),
                    func.count(NCR.id).filter(NCR.status == NCRStatus.CLOSED),
                )
                .where(*ncr_date_filters)
                .group_by(month_expr)
                .order_by(month_expr)
            )
        ).all()

        date_expr = func.to_char(NCR.edc_given_date, "YYYY-MM-DD").label("date")

        overdue_trend = (
            await self.session.execute(
                select(
                    date_expr,
                    func.count(NCR.id),
                )
                .where(
                    NCR.edc_given_date < func.now(),
                    NCR.status != NCRStatus.CLOSED,
                    *ncr_date_filters,
                )
                .group_by(date_expr)
                .order_by(date_expr)
            )
        ).all()

        plant_wise = (
            await self.session.execute(
                select(
                    Plant.name,
                    func.count(NCR.id),
                )
                .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
                .join(Audit, Audit.id == AuditInfo.audit_id)
                .join(Plant, Plant.id == Audit.plant_id)
                .where(*ncr_date_filters)
                .group_by(Plant.name)
            )
        ).all()

        dept_wise = (
            await self.session.execute(
                select(
                    Department.name,
                    func.count(NCR.id),
                )
                .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
                .join(Department, Department.id == AuditInfo.department_id)
                .where(*ncr_date_filters)
                .group_by(Department.name)
            )
        ).all()

        aging = (
            await self.session.execute(
                select(
                    case(
                        (
                            func.now() - NCR.created_at <= text("interval '7 days'"),
                            "0-7",
                        ),
                        (
                            func.now() - NCR.created_at <= text("interval '15 days'"),
                            "8-15",
                        ),
                        (
                            func.now() - NCR.created_at <= text("interval '30 days'"),
                            "16-30",
                        ),
                        else_="30+",
                    ).label("bucket"),
                    func.count(NCR.id),
                )
                .where(NCR.status != NCRStatus.CLOSED, *ncr_date_filters)
                .group_by("bucket")
            )
        ).all()

        root_cause = (
            await self.session.execute(
                select(NCR.root_cause, func.count(NCR.id))
                .where(NCR.root_cause.isnot(None), *ncr_date_filters)
                .group_by(NCR.root_cause)
            )
        ).all()

        # =========================
        # EXTRA ADMIN GRAPHS
        # =========================

        audit_type_ncrs = (
            await self.session.execute(
                select(
                    Audit.type,
                    func.count(NCR.id),
                )
                .join(AuditInfo, AuditInfo.audit_id == Audit.id)
                .join(NCR, NCR.audit_info_id == AuditInfo.id)
                .where(*ncr_date_filters)
                .group_by(Audit.type)
            )
        ).all()

        auditor_workload = (
            await self.session.execute(
                select(
                    User.name,
                    func.count(Followup.id),
                    func.count(Followup.id).filter(Followup.completed_on.isnot(None)),
                )
                .join(Followup, Followup.auditor_id == User.id)
                .group_by(User.name)
            )
        ).all()

        auditee_compliance = (
            await self.session.execute(
                select(
                    Department.name,
                    (
                        func.count(NCR.id).filter(NCR.status == NCRStatus.CLOSED)
                        * 100.0
                        / func.nullif(func.count(NCR.id), 0)
                    ),
                    (
                        func.count(NCR.id).filter(
                            NCR.edc_given_date < func.now(),
                            NCR.status != NCRStatus.CLOSED,
                        )
                        * 100.0
                        / func.nullif(func.count(NCR.id), 0)
                    ),
                )
                .join(AuditInfo, AuditInfo.department_id == Department.id)
                .join(NCR, NCR.audit_info_id == AuditInfo.id)
                .where(*ncr_date_filters)
                .group_by(Department.name)
            )
        ).all()

        followup_cycles = (
            await self.session.execute(
                select(
                    func.count(Followup.id),
                    func.count(NCR.id),
                )
                .join(NCR, NCR.id == Followup.ncr_id)
                .group_by(Followup.ncr_id)
            )
        ).all()

        edc_month_expr = func.to_char(
            func.date_trunc("month", EdcRequest.created_at), "YYYY-MM"
        ).label("month")

        edc_trend = (
            await self.session.execute(
                select(
                    edc_month_expr,
                    func.count(EdcRequest.id),
                )
                .group_by(edc_month_expr)
                .order_by(edc_month_expr)
            )
        ).all()

        rejection_reasons = (
            await self.session.execute(
                select(NCR.rejected_reson, func.count(NCR.id).label("count"))
                .where(NCR.rejected_reson.isnot(None), *ncr_date_filters)
                .group_by(NCR.rejected_reson)
            )
        ).all()

        audit_count = await self.session.scalar(
    select(func.count(Audit.id))
)

        ncr_count = await self.session.scalar(
            select(func.count(NCR.id))
        )

        audit_vs_ncr_ratio = (
            audit_count or 0,
            ncr_count or 0,
        )
   

        sla_buckets = (
            await self.session.execute(
                select(
                    func.count(NCR.id).filter(
                        func.extract(
                            "epoch",
                            NCR.actual_date_of_completion - NCR.created_at,
                        )
                        / 86400
                        <= 7
                    ),
                    func.count(NCR.id).filter(
                        func.extract(
                            "epoch",
                            NCR.actual_date_of_completion - NCR.created_at,
                        )
                        / 86400
                        <= 15
                    ),
                    func.count(NCR.id).filter(
                        func.extract(
                            "epoch",
                            NCR.actual_date_of_completion - NCR.created_at,
                        )
                        / 86400
                        > 15
                    ),
                ).where(NCR.status == NCRStatus.CLOSED, *ncr_date_filters)
            )
        ).one()

        repeat_ncrs = (
            await self.session.execute(
                select(
                    NCR.main_clause,
                    func.count(NCR.id),
                )
                .where(*ncr_date_filters)
                .group_by(NCR.main_clause)
                .having(func.count(NCR.id) > 1)
            )
        ).all()

        # =========================
        # COMPARISON (MONTH VS LAST)
        # =========================

        today = datetime.utcnow()
        start_current = today.replace(day=1)
        start_prev = (start_current - timedelta(days=1)).replace(day=1)

        prev_r, curr_r, prev_c, curr_c = (
            await self.session.execute(
                select(
                    func.count(NCR.id).filter(
                        NCR.created_at.between(start_prev, start_current)
                    ),
                    func.count(NCR.id).filter(NCR.created_at >= start_current),
                    func.count(NCR.id).filter(
                        NCR.status == NCRStatus.CLOSED,
                        NCR.created_at.between(start_prev, start_current),
                    ),
                    func.count(NCR.id).filter(
                        NCR.status == NCRStatus.CLOSED,
                        NCR.created_at >= start_current,
                    ),
                )
            )
        ).one()
        plant_comparison_rows = (
            await self.session.execute(
                select(
                    Plant.name,
                    (
                        func.count(NCR.id).filter(
                            NCR.edc_given_date < func.now(),
                            NCR.status != NCRStatus.CLOSED,
                        )
                        * 100.0
                        / func.nullif(func.count(NCR.id), 0)
                    ),
                    func.avg(
                        func.extract(
                            "epoch",
                            NCR.actual_date_of_completion - NCR.created_at,
                        )
                        / 86400
                    ),
                )
                .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
                .join(Audit, Audit.id == AuditInfo.audit_id)
                .join(Plant, Plant.id == Audit.plant_id)
                .where(*ncr_date_filters)
                .group_by(Plant.name)
            )
        ).all()

        plant_comparison = [
            {
                "plant": name,
                "overdue_pct": round(overdue or 0, 2),
                "avg_closure_days": round(avg_days or 0, 2),
            }
            for name, overdue, avg_days in plant_comparison_rows
        ]
        department_comparison_rows = (
            await self.session.execute(
                select(
                    Department.name,
                    (
                        func.count(NCR.id).filter(
                            NCR.edc_given_date < func.now(),
                            NCR.status != NCRStatus.CLOSED,
                        )
                        * 100.0
                        / func.nullif(func.count(NCR.id), 0)
                    ),
                    func.avg(
                        func.extract(
                            "epoch",
                            NCR.actual_date_of_completion - NCR.created_at,
                        )
                        / 86400
                    ),
                )
                .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
                .join(Audit, Audit.id == AuditInfo.audit_id)
                .join(Department, Department.id == AuditInfo.department_id)
                .where(*ncr_date_filters)
                .group_by(Department.name)
            )
        ).all()

        department_comparison = [
            {
                "department": name,
                "overdue_pct": round(overdue or 0, 2),
                "avg_closure_days": round(avg_days or 0, 2),
            }
            for name, overdue, avg_days in department_comparison_rows
        ]

        before_after = (
            await self.session.execute(
                select(
                    func.count(NCR.id).filter(NCR.rejected_count > 0),
                    func.count(NCR.id).filter(NCR.status == NCRStatus.CLOSED),
                ).where(*ncr_date_filters)
            )
        ).one()

        before_after_corrective_action = {
            "before": before_after[0] or 0,
            "after": before_after[1] or 0,
        }

        TARGET_DAYS = 10

        target_vs_actual = {
            "target_closure_days": TARGET_DAYS,
            "actual_avg_closure_days": avg_closure_days,
        }

        return {
            "stats": {
                "total_audits": total_audits or 0,
                "total_ncrs": total_ncrs or 0,
                "open_ncrs": open_ncrs or 0,
                "closed_ncrs": closed_ncrs or 0,
                "overdue_ncrs": overdue_ncrs or 0,
                "edc_compliance_pct": edc_compliance_pct,
                "avg_closure_days": avg_closure_days,
                "rejection_rate_pct": rejection_rate_pct,
                "edc_extension_requests": edc_extension_requests or 0,
            },
            "overview_graphs": {
                "ncr_status_distribution": [
                    {"status": s.value, "count": c} for s, c in status_dist
                ],
                "monthly_ncr_trend": [
                    {"month": m, "raised": r, "closed": c} for m, r, c in monthly_trend
                ],
                "overdue_ncr_trend": [
                    {"date": d, "count": c} for d, c in overdue_trend
                ],
                "plant_wise_ncrs": [{"label": p, "count": c} for p, c in plant_wise],
                "department_wise_ncrs": [
                    {"label": d, "count": c} for d, c in dept_wise
                ],
                "ncr_aging_buckets": [{"bucket": b, "count": c} for b, c in aging],
                "root_cause_distribution": [
                    {"label": r, "count": c} for r, c in root_cause
                ],
            },
            "extra_admin_graphs": {
                "audit_type_ncrs": [
                    {"label": t, "value": c} for t, c in audit_type_ncrs
                ],
                "auditor_workload": [
                    {"auditor": n, "assigned": a, "completed": c}
                    for n, a, c in auditor_workload
                ],
                "auditee_compliance": [
                    {
                        "auditee": n,
                        "closure_rate": round(cr or 0, 2),
                        "overdue_pct": round(op or 0, 2),
                    }
                    for n, cr, op in auditee_compliance
                ],
                "followup_cycles": [
                    {"label": f"{c} cycles", "value": n} for c, n in followup_cycles
                ],
                "edc_extension_trend": [{"label": m, "value": c} for m, c in edc_trend],
                "rejection_reasons": [
                    {"label": r or "Unknown", "value": c} for r, c in rejection_reasons
                ],
                "audit_vs_ncr_ratio": [
                    {"label": "Audits", "value": audit_vs_ncr_ratio[0]},
                    {"label": "NCRs", "value": audit_vs_ncr_ratio[1]},
                ],
                "sla_buckets": [
                    {"label": "0-7 Days", "value": sla_buckets[0]},
                    {"label": "8-15 Days", "value": sla_buckets[1]},
                    {"label": "15+ Days", "value": sla_buckets[2]},
                ],
                "repeat_ncrs": [{"label": c, "value": n} for c, n in repeat_ncrs],
            },
            "comparison_graphs": {
                "month_vs_last_month": {
                    "raised": {
                        "previous": prev_r or 0,
                        "current": curr_r or 0,
                    },
                    "closed": {
                        "previous": prev_c or 0,
                        "current": curr_c or 0,
                    },
                },
                "plant_comparison": plant_comparison,
                "department_comparison": department_comparison,
                "before_after_corrective_action": before_after_corrective_action,
                "target_vs_actual": target_vs_actual,
            },
        }


    async def get_hod_dashboard(
        self,
        plant_id: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        df = self._date_filters(NCR.created_at, from_date, to_date)

        # ---------------- KPIs ----------------

        total_audits = await self.session.scalar(
            select(func.count(Audit.id)).where(Audit.plant_id == plant_id)
        )

        audits_completed = await self.session.scalar(
            select(func.count(Audit.id))
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .where(Audit.plant_id == plant_id, AuditInfo.status == AuditInfoStatus.CLOSED)
        )

        audits_in_progress = await self.session.scalar(
            select(func.count(Audit.id))
             .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .where(Audit.plant_id == plant_id, AuditInfo.status == AuditInfoStatus.OPEN)
        )

        total_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(Audit.plant_id == plant_id, *df)
        )

        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(
                Audit.plant_id == plant_id,
                NCR.status != NCRStatus.CLOSED,
                *df
            )
        )

        overdue_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(
                Audit.plant_id == plant_id,
                NCR.edc_given_date < func.now(),
                NCR.status != NCRStatus.CLOSED,
                *df
            )
        )

        rejected_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(
                Audit.plant_id == plant_id,
                NCR.rejected_count > 0,
                *df
            )
        )

        avg_closure_days = await self.session.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        NCR.actual_date_of_completion - NCR.created_at
                    ) / 86400
                )
            )
            .join(AuditInfo).join(Audit)
            .where(
                Audit.plant_id == plant_id,
                NCR.status == NCRStatus.CLOSED,
                *df
            )
        )

        # ---------------- Charts ----------------

        audit_status = await self.session.execute(
            select(AuditInfo.status, func.count(Audit.id))
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .where(Audit.plant_id == plant_id)
            .group_by(AuditInfo.status)
        )

        dept_audit_coverage = await self.session.execute(
            select(Department.name, func.count(Audit.id))
            .join(AuditInfo, AuditInfo.department_id == Department.id)
            .join(Audit, Audit.id == AuditInfo.audit_id)
            .where(Audit.plant_id == plant_id)
            .group_by(Department.name)
        )

        dept_ncr = await self.session.execute(
            select(Department.name, func.count(NCR.id))
            .join(AuditInfo, AuditInfo.department_id == Department.id)
            .join(NCR, NCR.audit_info_id == AuditInfo.id)
            .join(Audit, Audit.id == AuditInfo.audit_id)
            .where(Audit.plant_id == plant_id, *df)
            .group_by(Department.name)
        )

        ncr_status = await self.session.execute(
            select(NCR.status, func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(Audit.plant_id == plant_id, *df)
            .group_by(NCR.status)
        )

        aging = await self.session.execute(
            select(
                case(
                    (func.now() - NCR.created_at <= text("interval '7 days'"), "0-7"),
                    (func.now() - NCR.created_at <= text("interval '15 days'"), "8-15"),
                    (func.now() - NCR.created_at <= text("interval '30 days'"), "16-30"),
                    else_="30+"
                ),
                func.count(NCR.id)
            )
            .join(AuditInfo).join(Audit)
            .where(
                Audit.plant_id == plant_id,
                NCR.status != NCRStatus.CLOSED,
                *df
            )
            .group_by(text("1"))
        )

        edc_status = await self.session.execute(
            select(EdcRequest.status, func.count(EdcRequest.id))
            .join(NCR).join(AuditInfo).join(Audit)
            .where(Audit.plant_id == plant_id)
            .group_by(EdcRequest.status)
        )

        followup_effectiveness = await self.session.execute(
            select(
                case(
                    (NCR.status == NCRStatus.CLOSED, "Closed"),
                    else_="Rejected"
                ),
                func.count(Followup.id)
            )
            .join(NCR).join(AuditInfo).join(Audit)
            .where(Audit.plant_id == plant_id)
            .group_by(text("1"))
        )

        auditor_workload = await self.session.execute(
            select(
                User.name,
                func.count(func.distinct(Audit.id)),
                func.count(NCR.id)
            )
            .join(AuditTeam, AuditTeam.user_id == User.id)
            .join(AuditInfo, AuditInfo.id == AuditTeam.audit_info_id)
            .join(Audit, Audit.id == AuditInfo.audit_id)
            .outerjoin(NCR, NCR.audit_info_id == AuditInfo.id)
            .where(Audit.plant_id == plant_id)
            .group_by(User.name)
        )

        clause_wise = await self.session.execute(
            select(NCR.main_clause, func.count(NCR.id))
            .join(AuditInfo).join(Audit)
            .where(Audit.plant_id == plant_id)
            .group_by(NCR.main_clause)
        )

        audit_delay = await self.session.execute(
            select(Audit.end_date, NCR.actual_date_of_completion)
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .join(NCR, NCR.audit_info_id == AuditInfo.id)
            .where(Audit.plant_id == plant_id, NCR.status == NCRStatus.CLOSED)
        )

        # ---------------- RETURN ----------------

        return {
    "stats": {
        "total_audits": total_audits,
        "audits_completed": audits_completed,
        "audits_in_progress": audits_in_progress,
        "total_ncrs": total_ncrs,
        "open_ncrs": open_ncrs,
        "overdue_ncrs": overdue_ncrs,
        "rejected_ncrs": rejected_ncrs,
        "avg_ncr_closure_days": round(avg_closure_days or 0, 2),
    },
    "charts": {
        "audit_status_distribution": [
            {"status": s.value if hasattr(s, "value") else str(s), "count": c}
            for s, c in audit_status
        ],

        "department_audit_coverage": [
            {"name": d, "count": c}
            for d, c in dept_audit_coverage
        ],

        "department_ncr_distribution": [
            {"name": d, "count": c}
            for d, c in dept_ncr
        ],

        "ncr_status_distribution": [
            {"status": s.value if hasattr(s, "value") else str(s), "count": c}
            for s, c in ncr_status
        ],

        "ncr_aging": [
            {"bucket": b, "count": c}
            for b, c in aging
        ],

        "edc_status_distribution": [
            {"status": s.value if hasattr(s, "value") else str(s), "count": c}
            for s, c in edc_status
        ],

        "followup_effectiveness": [
            {"label": l, "count": c}
            for l, c in followup_effectiveness
        ],

        "auditor_workload": [
            {
                "auditor": name,
                "audits_count": audits,
                "ncrs_count": ncrs
            }
            for name, audits, ncrs in auditor_workload
        ],

        "clause_wise_ncrs": [
            {"label": clause or "Unknown", "count": c}
            for clause, c in clause_wise
        ],

        "ncr_delay_trend": [
            {
                "planned_end_date": planned,
                "actual_end_date": actual
            }
            for planned, actual in audit_delay
        ],
    },
}



    async def get_auditee_dashboard(
        self,
        auditee_id: str,
        department_ids: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        ncr_date_filters = self._date_filters(NCR.created_at, from_date, to_date)

        auditee_ncr_ids = (
            select(NCR.id)
            .join(NCRTeam, NCRTeam.ncr_id == NCR.id)
            .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
            .where(
                NCRTeam.user_id == auditee_id,
                NCRTeam.role == NCRTeamRole.AUDITEE,
                AuditInfo.department_id.in_([department_ids]),
                *ncr_date_filters,
            )
            .subquery()
        )

        # ==================================================
        # KPIs
        # ==================================================

        total_ncrs = await self.session.scalar(
            select(func.count(auditee_ncr_ids.c.id))
        )

        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.id.in_(select(auditee_ncr_ids.c.id)),
                NCR.status != NCRStatus.CLOSED,
            )
        )

        overdue_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.id.in_(select(auditee_ncr_ids.c.id)),
                NCR.edc_given_date < func.now(),
                NCR.status != NCRStatus.CLOSED,
            )
        )

        rejected_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.id.in_(select(auditee_ncr_ids.c.id)),
                NCR.rejected_count > 0,
            )
        )

        avg_closure_days = await self.session.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        NCR.actual_date_of_completion - NCR.created_at,
                    ) / 86400
                )
            )
            .where(
                NCR.id.in_(select(auditee_ncr_ids.c.id)),
                NCR.status == NCRStatus.CLOSED,
            )
        )

        # ==================================================
        # CHARTS
        # ==================================================

        lifecycle = (
            await self.session.execute(
                select(
                    func.count(NCR.id),
                    func.count(NCR.id).filter(NCR.root_cause.isnot(None)),
                    func.count(NCR.id).filter(NCR.corrective_action_details.isnot(None)),
                    func.count(NCR.id).filter(NCR.edc_given_date.isnot(None)),
                    func.count(NCR.id).filter(Followup.completed_on.isnot(None)),
                    func.count(NCR.id).filter(NCR.status == NCRStatus.CLOSED),
                )
                .outerjoin(Followup, Followup.ncr_id == NCR.id)
                .where(NCR.id.in_(select(auditee_ncr_ids.c.id)))
            )
        ).one()

        corrective_delay = (
            await self.session.execute(
                select(
                    case(
                        (NCR.actual_date_of_completion <= NCR.followup_date, "On Time"),
                        else_="Delayed",
                    ),
                    func.count(NCR.id),
                )
                .where(NCR.id.in_(select(auditee_ncr_ids.c.id)))
                .group_by(text("1"))
            )
        ).all()

        root_causes = (
            await self.session.execute(
                select(NCR.root_cause, func.count(NCR.id))
                .where(
                    NCR.id.in_(select(auditee_ncr_ids.c.id)),
                    NCR.root_cause.isnot(None),
                )
                .group_by(NCR.root_cause)
            )
        ).all()

        edc_status = (
            await self.session.execute(
                select(EdcRequest.status, func.count(EdcRequest.id))
                .join(NCR)
                .where(NCR.id.in_(select(auditee_ncr_ids.c.id)))
                .group_by(EdcRequest.status)
            )
        ).all()

        rejection_reasons = (
            await self.session.execute(
                select(NCR.rejected_reson, func.count(NCR.id))
                .where(
                    NCR.id.in_(select(auditee_ncr_ids.c.id)),
                    NCR.rejected_reson.isnot(None),
                )
                .group_by(NCR.rejected_reson)
            )
        ).all()

        clause_wise = (
            await self.session.execute(
                select(NCR.main_clause, func.count(NCR.id))
                .where(NCR.id.in_(select(auditee_ncr_ids.c.id)))
                .group_by(NCR.main_clause)
            )
        ).all()

        # ==================================================
        # RETURN
        # ==================================================

        return {
            "stats": {
                "total_ncrs": total_ncrs or 0,
                "open_ncrs": open_ncrs or 0,
                "overdue_ncrs": overdue_ncrs or 0,
                "rejected_ncrs": rejected_ncrs or 0,
                "avg_closure_days": round(avg_closure_days or 0, 2),
            },
            "charts": {
                "ncr_lifecycle_funnel": [
                    {"stage": "Raised", "count": lifecycle[0]},
                    {"stage": "Root Cause", "count": lifecycle[1]},
                    {"stage": "Corrective Action", "count": lifecycle[2]},
                    {"stage": "EDC Submitted", "count": lifecycle[3]},
                    {"stage": "Follow-up Done", "count": lifecycle[4]},
                    {"stage": "Closed", "count": lifecycle[5]},
                ],
              "corrective_action_delay": [
    {"label": s, "count": c} for s, c in corrective_delay
],

                "root_cause_distribution": [
                    {"label": r or "Unknown", "count": c} for r, c in root_causes
                ],
               "edc_status_distribution": [
    {"status": s.value, "count": c} for s, c in edc_status
],

                "rejection_reasons": [
                    {"label": r or "Unknown", "count": c}
                    for r, c in rejection_reasons
                ],
                "clause_wise_ncrs": [
                    {"label": c or "Unknown", "count": n} for c, n in clause_wise
                ],
            },
        }






    async def get_auditor_dashboard(
        self,
        auditor_id: str,
        department_ids: str,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ):
        ncr_date_filters = self._date_filters(NCR.created_at, from_date, to_date)

        # ==================================================
        # BASE SCOPES
        # ==================================================

        auditor_audit_ids = (
            select(Audit.id)
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .join(AuditTeam, AuditTeam.audit_info_id == AuditInfo.id)
            
            .where(
                AuditTeam.user_id == auditor_id,
                AuditInfo.department_id.in_([department_ids]),
                AuditTeam.role == AuditTeamRole.AUDITOR,
            )
            .subquery()
        )

        auditor_ncr_ids = (
            select(NCR.id)
            .join(AuditInfo, AuditInfo.id == NCR.audit_info_id)
            .join(AuditTeam, AuditTeam.audit_info_id == AuditInfo.id)
            .join(NCRTeam, NCRTeam.ncr_id == NCR.id)
            .where(
                AuditTeam.user_id == auditor_id,
                AuditInfo.department_id.in_([department_ids]),
                NCRTeam.user_id == auditor_id,
                NCRTeam.role == NCRTeamRole.CREATED_BY,
                *ncr_date_filters,
            )
            .subquery()
        )

        # ==================================================
        # KPIs
        # ==================================================

        assigned_audits = await self.session.scalar(
            select(func.count(func.distinct(auditor_audit_ids.c.id)))
        )

        audits_completed = await self.session.scalar(
            select(func.count(Audit.id))
            .join(AuditInfo, AuditInfo.audit_id == Audit.id)
            .where(
                Audit.id.in_(select(auditor_audit_ids.c.id)),
                AuditInfo.status == "CLOSED",
            )
        )

        ncrs_raised = await self.session.scalar(
            select(func.count(auditor_ncr_ids.c.id))
        )

        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.id.in_(select(auditor_ncr_ids.c.id)),
                NCR.status != NCRStatus.CLOSED,
            )
        )

        avg_closure_days = await self.session.scalar(
            select(
                func.avg(
                    func.extract(
                        "epoch",
                        NCR.actual_date_of_completion - NCR.created_at,
                    ) / 86400
                )
            )
            .where(
                NCR.id.in_(select(auditor_ncr_ids.c.id)),
                NCR.status == NCRStatus.CLOSED,
            )
        )

        followups_assigned = await self.session.scalar(
            select(func.count(Followup.id))
            .where(Followup.auditor_id == auditor_id)
        )

        # ==================================================
        # CHARTS
        # ==================================================

        audit_status = (
            await self.session.execute(
                select(AuditInfo.status, func.count(Audit.id))
                .join(AuditInfo, AuditInfo.audit_id == Audit.id)
                .where(Audit.id.in_(select(auditor_audit_ids.c.id)))
                .group_by(AuditInfo.status)
            )
        ).all()

        ncr_trend = (
            await self.session.execute(
                select(
                    func.to_char(func.date_trunc("month", NCR.created_at), "YYYY-MM"),
                    func.count(NCR.id),
                )
                .where(NCR.id.in_(select(auditor_ncr_ids.c.id)))
                .group_by(text("1"))
                .order_by(text("1"))
            )
        ).all()

        ncr_status = (
            await self.session.execute(
                select(NCR.status, func.count(NCR.id))
                .where(NCR.id.in_(select(auditor_ncr_ids.c.id)))
                .group_by(NCR.status)
            )
        ).all()

        severity_mode = (
            await self.session.execute(
                select(NCR.mode, func.count(NCR.id))
                .where(NCR.id.in_(select(auditor_ncr_ids.c.id)))
                .group_by(NCR.mode)
            )
        ).all()

        aging = (
            await self.session.execute(
                select(
                    case(
                        (func.now() - NCR.created_at <= text("interval '7 days'"), "0-7"),
                        (func.now() - NCR.created_at <= text("interval '15 days'"), "8-15"),
                        (func.now() - NCR.created_at <= text("interval '30 days'"), "16-30"),
                        else_="30+",
                    ),
                    func.count(NCR.id),
                )
                .where(
                    NCR.id.in_(select(auditor_ncr_ids.c.id)),
                    NCR.status != NCRStatus.CLOSED,
                )
                .group_by(text("1"))
            )
        ).all()

        clause_wise = (
            await self.session.execute(
                select(NCR.main_clause, func.count(NCR.id))
                .where(NCR.id.in_(select(auditor_ncr_ids.c.id)))
                .group_by(NCR.main_clause)
            )
        ).all()

        followup_outcome = (
            await self.session.execute(
                select(Followup.status, func.count(Followup.id))
                .where(Followup.auditor_id == auditor_id)
                .group_by(Followup.status)
            )
        ).all()

        pending_edc_reviews = (
            await self.session.execute(
                select(EdcRequest.id, NCR.id)
                .join(NCR)
                .where(
                    NCR.id.in_(select(auditor_ncr_ids.c.id)),
                    EdcRequest.status == EDCStatus.PENDING,
                )
            )
        ).all()

     
        return {
            "stats": {
                "assigned_audits": assigned_audits or 0,
                "audits_completed": audits_completed or 0,
                "ncrs_raised": ncrs_raised or 0,
                "open_ncrs": open_ncrs or 0,
                "followups_assigned": followups_assigned or 0,
                "avg_closure_days": round(avg_closure_days or 0, 2),
            },
            "charts": {
                "audit_status_distribution": [
                    {"status": s.value, "count": c} for s, c in audit_status
                ],
                "ncr_monthly_trend": [
                    {"month": m, "count": c} for m, c in ncr_trend
                ],
                "ncr_status_distribution": [
                    {"status": s.value, "count": c} for s, c in ncr_status
                ],
                "ncr_severity_mode": [
                    {"label": m, "count": c} for m, c in severity_mode
                ],
                "ncr_aging": [
                    {"bucket": b, "count": c} for b, c in aging
                ],
                "clause_wise_ncrs": [
                    {"label": c or "Unknown", "count": n} for c, n in clause_wise
                ],
                "followup_outcome": [
                    {"status": s, "count": c} for s, c in followup_outcome
                ],
            },
            "tables": {
                "pending_edc_reviews": [
                    {"edc_id": e, "ncr_id": n} for e, n in pending_edc_reviews
                ]
            },
        }

    async def get_audit_info_dashboard(self, audit_info_id: str):


        total_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(NCR.audit_info_id == audit_info_id)
        )

        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.audit_info_id == audit_info_id,
                NCR.status != NCRStatus.CLOSED
            )
        )

        closed_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.audit_info_id == audit_info_id,
                NCR.status == NCRStatus.CLOSED
            )
        )

        overdue_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .where(
                NCR.audit_info_id == audit_info_id,
                NCR.edc_given_date < func.now(),
                NCR.status != NCRStatus.CLOSED
            )
        )

        total_edc = await self.session.scalar(
            select(func.count(EdcRequest.id))
            .join(NCR)
            .where(NCR.audit_info_id == audit_info_id)
        )

        pending_edc = await self.session.scalar(
            select(func.count(EdcRequest.id))
            .join(NCR)
            .where(
                NCR.audit_info_id == audit_info_id,
                EdcRequest.status == EDCStatus.PENDING
            )
        )

        total_followups = await self.session.scalar(
            select(func.count(Followup.id))
            .join(NCR)
            .where(NCR.audit_info_id == audit_info_id)
        )


        ncr_status = (
            await self.session.execute(
                select(NCR.status, func.count())
                .where(NCR.audit_info_id == audit_info_id)
                .group_by(NCR.status)
            )
        ).all()

        edc_status = (
            await self.session.execute(
                select(EdcRequest.status, func.count())
                .join(NCR)
                .where(NCR.audit_info_id == audit_info_id)
                .group_by(EdcRequest.status)
            )
        ).all()

        followup_status = (
            await self.session.execute(
                select(Followup.status, func.count())
                .join(NCR)
                .where(NCR.audit_info_id == audit_info_id)
                .group_by(Followup.status)
            )
        ).all()

        aging = (
            await self.session.execute(
                select(
                    case(
                        (func.now() - NCR.created_at <= text("interval '7 days'"), "0-7"),
                        (func.now() - NCR.created_at <= text("interval '15 days'"), "8-15"),
                        (func.now() - NCR.created_at <= text("interval '30 days'"), "16-30"),
                        else_="30+"
                    ),
                    func.count(NCR.id)
                )
                .where(
                    NCR.audit_info_id == audit_info_id,
                    NCR.status != NCRStatus.CLOSED
                )
                .group_by(text("1"))
            )
        ).all()

        root_cause = (
            await self.session.execute(
                select(NCR.root_cause, func.count())
                .where(NCR.audit_info_id == audit_info_id)
                .group_by(NCR.root_cause)
            )
        ).all()

        clause = (
            await self.session.execute(
                select(NCR.main_clause, func.count())
                .where(NCR.audit_info_id == audit_info_id)
                .group_by(NCR.main_clause)
            )
        ).all()

        return {
            "stats": {
                "total_ncrs": total_ncrs or 0,
                "open_ncrs": open_ncrs or 0,
                "closed_ncrs": closed_ncrs or 0,
                "overdue_ncrs": overdue_ncrs or 0,
                "total_edc": total_edc or 0,
                "pending_edc": pending_edc or 0,
                "total_followups": total_followups or 0,
            },
            "charts": {
                "ncr_status_distribution": [
                    {"status": s.value, "count": c} for s, c in ncr_status
                ],
                "edc_status_distribution": [
                    {"status": s.value, "count": c} for s, c in edc_status
                ],
                "followup_status_distribution": [
                    {"status": s, "count": c} for s, c in followup_status
                ],
                "ncr_aging": [
                    {"bucket": b, "count": c} for b, c in aging
                ],
                "root_cause_distribution": [
                    {"label": r or "Unknown", "count": c}
                    for r, c in root_cause
                ],
                "clause_distribution": [
                    {"label": cl or "Unknown", "count": c}
                    for cl, c in clause
                ],
            }
        }
            
    async def get_audit_dashboard(self, audit_id: str):
        # 1. Base query filter for reuse
        # Note: We filter by AuditInfo.audit_id which is the UUID passed in.
        
        # Total NCRs
        total_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .where(AuditInfo.audit_id == audit_id)
        )

        # Open NCRs
        open_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .where(
                AuditInfo.audit_id == audit_id,
                NCR.status != NCRStatus.CLOSED
            )
        )

        # Overdue NCRs
        overdue_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .where(
                AuditInfo.audit_id == audit_id,
                NCR.edc_given_date < func.now(),
                NCR.status != NCRStatus.CLOSED
            )
        )

        # Rejected NCRs
        rejected_ncrs = await self.session.scalar(
            select(func.count(NCR.id))
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .where(
                AuditInfo.audit_id == audit_id,
                NCR.rejected_count > 0
            )
        )

        # Repeat NCRs (Count of clauses appearing more than once)
        # We use a subquery here to correctly count how many clauses are "repeats"
        repeat_ncr_query = (
            select(NCR.main_clause)
            .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
            .where(AuditInfo.audit_id == audit_id)
            .group_by(NCR.main_clause)
            .having(func.count(NCR.id) > 1)
        ).subquery()
        
        repeat_ncr = await self.session.scalar(
            select(func.count()).select_from(repeat_ncr_query)
        )

        # Calculate Risk Score
        risk_score = (
            (open_ncrs or 0) * 2 +
            (overdue_ncrs or 0) * 3 +
            (rejected_ncrs or 0) * 2 +
            (repeat_ncr or 0) * 4
        )

        # Department Risk Breakdown
        dept_risk = (
            await self.session.execute(
                select(
                    Department.name,
                    func.count(NCR.id),
                    func.sum(case((NCR.rejected_count > 0, 1), else_=0)),
                    func.sum(case((NCR.edc_given_date < func.now(), 1), else_=0))
                )
                .select_from(Department)
                .join(AuditInfo, AuditInfo.department_id == Department.id)
                .join(NCR, NCR.audit_info_id == AuditInfo.id)
                .where(AuditInfo.audit_id == audit_id)
                .group_by(Department.name)
            )
        ).all()

        # Clause Heatmap
        clause_heatmap = (
            await self.session.execute(
                select(
                    NCR.main_clause,
                    Department.name,
                    func.count(NCR.id)
                )
                .join(AuditInfo, NCR.audit_info_id == AuditInfo.id)
                .join(Department, Department.id == AuditInfo.department_id)
                .where(AuditInfo.audit_id == audit_id)
                .group_by(NCR.main_clause, Department.name)
            )
        ).all()

        # EDC Requests by Department
        edc_by_dept = (
            await self.session.execute(
                select(
                    Department.name,
                    func.count(EdcRequest.id)
                )
                .join(AuditInfo, AuditInfo.department_id == Department.id)
                .join(NCR, NCR.audit_info_id == AuditInfo.id)
                .join(EdcRequest, EdcRequest.ncr_id == NCR.id)
                .where(AuditInfo.audit_id == audit_id)
                .group_by(Department.name)
            )
        ).all()

        return {
            "stats": {
                "total_ncrs": total_ncrs or 0,
                "open_ncrs": open_ncrs or 0,
                "overdue_ncrs": overdue_ncrs or 0,
                "rejected_ncrs": rejected_ncrs or 0,
                "plant_risk_score": risk_score
            },
            "graphs": {
                "department_risk": [
                    {
                        "department": d,
                        "total_ncr": total,
                        "rejected": rej or 0,
                        "overdue": od or 0
                    }
                    for d, total, rej, od in dept_risk
                ],
                "clause_heatmap": [
                    {
                        "clause": c,
                        "department": d,
                        "count": n
                    }
                    for c, d, n in clause_heatmap
                ],
                "edc_by_department": [
                    {"label": d, "count": c}
                    for d, c in edc_by_dept
                ]
            }
        }