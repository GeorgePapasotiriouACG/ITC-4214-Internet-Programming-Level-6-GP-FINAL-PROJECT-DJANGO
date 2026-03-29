# =============================================================================
# Author:       George Papasotiriou
# Date Created: March 28, 2026
# Project:      TrendMart E-Commerce Platform
# File:         shop/migrations/0004_aiconversation_userprofile_ai_preferences.py
# Description:  Adds:
#               1. AIConversation model — persistent per-user AI chat history
#                  stored in the DB so conversations survive session expiry and
#                  work across multiple devices.
#               2. UserProfile.ai_preferences JSONField — long-term AI memory
#                  that stores learned user preferences (brands, budget, sizes).
# =============================================================================

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # Must run after the review_photo migration (latest before this)
        ('shop', '0003_productrating_review_photo'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. Add ai_preferences to UserProfile ──────────────────────────────
        # Stores AI-learned preferences as a flexible JSON blob.
        # default=dict avoids the common mutable-default pitfall.
        migrations.AddField(
            model_name='userprofile',
            name='ai_preferences',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Stores long-term AI-learned user preferences (brands, budget, sizes, etc.)',
            ),
        ),

        # ── 2. Create AIConversation model ────────────────────────────────────
        # One row per chat message (user or assistant role).
        migrations.CreateModel(
            name='AIConversation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('role', models.CharField(
                    choices=[('user', 'User'), ('assistant', 'Assistant')],
                    max_length=10,
                )),
                ('content', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='ai_conversations',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'AI Conversation Message',
                'verbose_name_plural': 'AI Conversation Messages',
                'ordering': ['created_at'],
            },
        ),

        # Composite index for fast "last N messages for user X" queries
        migrations.AddIndex(
            model_name='aiconversation',
            index=models.Index(fields=['user', 'created_at'], name='shop_aiconv_user_id_idx'),
        ),
    ]
