"""replaced blacklist token model field with naive datetime

Revision ID: b7f5b0637509
Revises: 4666afdefb86
Create Date: 2024-11-05 01:37:03.002084

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7f5b0637509'
down_revision: Union[str, None] = '4666afdefb86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###