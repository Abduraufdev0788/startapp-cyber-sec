"""0001_initial_schema

Revision ID: c2240e1df345
Revises: 
Create Date: 2026-10-27 17:36:40.792613

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c2240e1df345'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='USER', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. telegram_accounts
    op.create_table(
        'telegram_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=False),
        sa.Column('phone_number_hash', sa.String(length=64), nullable=False),
        sa.Column('encrypted_session', sa.LargeBinary(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='CONNECTED', nullable=False),
        sa.Column('auth_state', sa.String(length=32), server_default='AUTHORIZED', nullable=False),
        sa.Column('last_connected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_telegram_accounts_id', 'telegram_accounts', ['id'])
    op.create_index('ix_telegram_accounts_user_id', 'telegram_accounts', ['user_id'])
    op.create_index('ix_telegram_accounts_telegram_user_id', 'telegram_accounts', ['telegram_user_id'], unique=True)
    op.create_index('ix_telegram_accounts_phone_number_hash', 'telegram_accounts', ['phone_number_hash'])
    op.create_index('ix_telegram_accounts_status', 'telegram_accounts', ['status'])

    # 3. telegram_chats
    op.create_table(
        'telegram_chats',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('telegram_accounts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('is_monitored', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_telegram_chats_id', 'telegram_chats', ['id'])
    op.create_index('ix_telegram_chats_account_id', 'telegram_chats', ['account_id'])
    op.create_index('ix_telegram_chats_telegram_chat_id', 'telegram_chats', ['telegram_chat_id'])

    # 4. telegram_messages
    op.create_table(
        'telegram_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('chat_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('telegram_chats.id', ondelete='CASCADE'), nullable=False),
        sa.Column('telegram_message_id', sa.BigInteger(), nullable=False),
        sa.Column('sender_id', sa.BigInteger(), nullable=True),
        sa.Column('sender_username', sa.String(length=255), nullable=True),
        sa.Column('has_urls', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('url_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('message_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_telegram_messages_id', 'telegram_messages', ['id'])
    op.create_index('ix_telegram_messages_chat_id', 'telegram_messages', ['chat_id'])
    op.create_index('ix_telegram_messages_telegram_message_id', 'telegram_messages', ['telegram_message_id'])

    # 5. scanned_urls
    op.create_table(
        'scanned_urls',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('url_hash', sa.CHAR(length=64), nullable=False),
        sa.Column('raw_url', sa.Text(), nullable=False),
        sa.Column('canonical_url', sa.Text(), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('last_scanned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_scanned_urls_id', 'scanned_urls', ['id'])
    op.create_index('ix_scanned_urls_url_hash', 'scanned_urls', ['url_hash'], unique=True)
    op.create_index('ix_scanned_urls_domain', 'scanned_urls', ['domain'])
    op.create_index('ix_scanned_urls_status', 'scanned_urls', ['status'])

    # 6. threat_intelligence
    op.create_table(
        'threat_intelligence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('url_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scanned_urls.id', ondelete='CASCADE'), nullable=False),
        sa.Column('domain_age_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('registrar', sa.String(length=255), nullable=True),
        sa.Column('dns_records', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('ssl_issuer', sa.String(length=255), nullable=True),
        sa.Column('ssl_valid', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('response_time_ms', sa.Integer(), nullable=True),
        sa.Column('has_login_form', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('has_password_input', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('redirect_chain', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('text_excerpt', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_threat_intelligence_id', 'threat_intelligence', ['id'])
    op.create_index('ix_threat_intelligence_url_id', 'threat_intelligence', ['url_id'], unique=True)

    # 7. threat_assessments
    op.create_table(
        'threat_assessments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('url_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scanned_urls.id', ondelete='CASCADE'), nullable=False),
        sa.Column('verdict', sa.String(length=32), nullable=False),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('confidence', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('impersonated_brand', sa.String(length=128), nullable=True),
        sa.Column('reasons', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('gemini_response', postgresql.JSONB(), nullable=True),
        sa.Column('evaluated_by', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_threat_assessments_id', 'threat_assessments', ['id'])
    op.create_index('ix_threat_assessments_url_id', 'threat_assessments', ['url_id'], unique=True)
    op.create_index('ix_threat_assessments_verdict', 'threat_assessments', ['verdict'])
    op.create_index('ix_threat_assessments_risk_score', 'threat_assessments', ['risk_score'])

    # 8. notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('scanned_urls.id', ondelete='CASCADE'), nullable=False),
        sa.Column('telegram_chat_id', sa.BigInteger(), nullable=False),
        sa.Column('alert_type', sa.String(length=64), nullable=False),
        sa.Column('delivery_status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_dismissed', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('dismissed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_notifications_id', 'notifications', ['id'])
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('ix_notifications_url_id', 'notifications', ['url_id'])
    op.create_index('ix_notifications_delivery_status', 'notifications', ['delivery_status'])
    op.create_index('ix_notifications_is_dismissed', 'notifications', ['is_dismissed'])

    # 9. audit_logs
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=255), nullable=True),
        sa.Column('details', postgresql.JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('ix_audit_logs_id', 'audit_logs', ['id'])
    op.create_index('ix_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('notifications')
    op.drop_table('threat_assessments')
    op.drop_table('threat_intelligence')
    op.drop_table('scanned_urls')
    op.drop_table('telegram_messages')
    op.drop_table('telegram_chats')
    op.drop_table('telegram_accounts')
    op.drop_table('users')
