"""convert composite pk to single id pk for userdepartment

Revision ID: 486e845eedf4
Revises: b7a7d9408bc1
Create Date: 2026-02-26

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = "486e845eedf4"
down_revision: Union[str, Sequence[str], None] = "b7a7d9408bc1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1️⃣ Add id column as NULLABLE first
    op.add_column(
        "userdepartment",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2️⃣ Ensure pgcrypto exists (safe if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 3️⃣ Populate existing rows with UUID
    op.execute("UPDATE userdepartment SET id = gen_random_uuid()")

    # 4️⃣ Make id NOT NULL
    op.alter_column(
        "userdepartment",
        "id",
        nullable=False,
    )

    # 5️⃣ Drop old composite primary key
    op.drop_constraint(
        "userdepartment_pkey",
        "userdepartment",
        type_="primary",
    )

    # 6️⃣ Create new primary key on id
    op.create_primary_key(
        "pk_userdepartment",
        "userdepartment",
        ["id"],
    )


def downgrade() -> None:
    # 1️⃣ Drop new primary key
    op.drop_constraint(
        "pk_userdepartment",
        "userdepartment",
        type_="primary",
    )

    # 2️⃣ Restore old composite primary key
    op.create_primary_key(
        "userdepartment_pkey",
        "userdepartment",
        ["user_id", "department_id", "role_id"],
    )

    # 3️⃣ Drop id column
    op.drop_column("userdepartment", "id")