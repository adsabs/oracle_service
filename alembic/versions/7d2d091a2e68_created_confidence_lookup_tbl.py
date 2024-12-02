"""created confidence value lookup tbl

Revision ID: 7d2d091a2e68
Revises: 723cf7ed45d5
Create Date: 2023-04-19 10:11:14.923289

"""

# revision identifiers, used by Alembic.
revision = '7d2d091a2e68'
down_revision = '723cf7ed45d5'

from alembic import op
import sqlalchemy as sa




def upgrade():
    #with app.app_context() as c:
    #   db.session.add(Model())
    #   db.session.commit()

    # ### commands auto generated by Alembic - please adjust! ###
    confidence_lookup_table = op.create_table('confidence_lookup',
    sa.Column('source', sa.String(), nullable=False, primary_key=True),
    sa.Column('confidence', sa.Float(), nullable=False),
    sa.PrimaryKeyConstraint('source')
    )

    op.bulk_insert(confidence_lookup_table, [
        {'source': 'ADS', 'confidence': 1.3},
        {'source': 'incorrect', 'confidence': -1},
        {'source': 'author', 'confidence': 1.2},
        {'source': 'publisher', 'confidence': 1.1},
        {'source': 'SPIRES', 'confidence': 1.05},
    ])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('confidence_value_lookup')
    # ### end Alembic commands ###