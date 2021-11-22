"""add white rabbit status

Revision ID: 63b625cf7b06
Revises: e83aa47e530b
Create Date: 2019-12-06 02:45:01.418693+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "63b625cf7b06"
down_revision = "e83aa47e530b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "node_white_rabbit_status",
        sa.Column("node_time", sa.BigInteger(), nullable=False),
        sa.Column("node", sa.Integer(), nullable=False),
        sa.Column("board_info_str", sa.String(), nullable=True),
        sa.Column("aliases", sa.String(), nullable=True),
        sa.Column("ip", sa.String(), nullable=True),
        sa.Column("mode", sa.String(), nullable=True),
        sa.Column("serial", sa.String(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("build_date", sa.BigInteger(), nullable=True),
        sa.Column("gw_date", sa.BigInteger(), nullable=True),
        sa.Column("gw_version", sa.String(), nullable=True),
        sa.Column("gw_id", sa.String(), nullable=True),
        sa.Column("build_hash", sa.String(), nullable=True),
        sa.Column("manufacture_tag", sa.String(), nullable=True),
        sa.Column("manufacture_device", sa.String(), nullable=True),
        sa.Column("manufacture_date", sa.BigInteger(), nullable=True),
        sa.Column("manufacture_partnum", sa.String(), nullable=True),
        sa.Column("manufacture_serial", sa.String(), nullable=True),
        sa.Column("manufacture_vendor", sa.String(), nullable=True),
        sa.Column("port0_ad", sa.Integer(), nullable=True),
        sa.Column("port0_link_asymmetry_ps", sa.Integer(), nullable=True),
        sa.Column("port0_manual_phase_ps", sa.Integer(), nullable=True),
        sa.Column("port0_clock_offset_ps", sa.Integer(), nullable=True),
        sa.Column("port0_cable_rt_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_master_slave_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_master_rx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_slave_rx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_master_tx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_slave_tx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port0_hd", sa.Integer(), nullable=True),
        sa.Column("port0_link", sa.Boolean(), nullable=True),
        sa.Column("port0_lock", sa.Boolean(), nullable=True),
        sa.Column("port0_md", sa.Integer(), nullable=True),
        sa.Column("port0_rt_time_ps", sa.Integer(), nullable=True),
        sa.Column("port0_nsec", sa.Integer(), nullable=True),
        sa.Column("port0_packets_received", sa.Integer(), nullable=True),
        sa.Column("port0_phase_setpoint_ps", sa.Integer(), nullable=True),
        sa.Column("port0_servo_state", sa.String(), nullable=True),
        sa.Column("port0_sv", sa.Integer(), nullable=True),
        sa.Column("port0_sync_source", sa.String(), nullable=True),
        sa.Column("port0_packets_sent", sa.Integer(), nullable=True),
        sa.Column("port0_update_counter", sa.Integer(), nullable=True),
        sa.Column("port0_time", sa.BigInteger(), nullable=True),
        sa.Column("port1_ad", sa.Integer(), nullable=True),
        sa.Column("port1_link_asymmetry_ps", sa.Integer(), nullable=True),
        sa.Column("port1_manual_phase_ps", sa.Integer(), nullable=True),
        sa.Column("port1_clock_offset_ps", sa.Integer(), nullable=True),
        sa.Column("port1_cable_rt_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_master_slave_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_master_rx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_slave_rx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_master_tx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_slave_tx_phy_delay_ps", sa.Integer(), nullable=True),
        sa.Column("port1_hd", sa.Integer(), nullable=True),
        sa.Column("port1_link", sa.Boolean(), nullable=True),
        sa.Column("port1_lock", sa.Boolean(), nullable=True),
        sa.Column("port1_md", sa.Integer(), nullable=True),
        sa.Column("port1_rt_time_ps", sa.Integer(), nullable=True),
        sa.Column("port1_nsec", sa.Integer(), nullable=True),
        sa.Column("port1_packets_received", sa.Integer(), nullable=True),
        sa.Column("port1_phase_setpoint_ps", sa.Integer(), nullable=True),
        sa.Column("port1_servo_state", sa.String(), nullable=True),
        sa.Column("port1_sv", sa.Integer(), nullable=True),
        sa.Column("port1_sync_source", sa.String(), nullable=True),
        sa.Column("port1_packets_sent", sa.Integer(), nullable=True),
        sa.Column("port1_update_counter", sa.Integer(), nullable=True),
        sa.Column("port1_time", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("node_time", "node"),
    )


def downgrade():
    op.drop_table("node_white_rabbit_status")
