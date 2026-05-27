from rest_framework import serializers

from accounts.models import NotificationDeliveryLog, OnboardingLifecycleSendLog
from accounts.services.onboarding.lifecycle_digest_review import (
    DIGEST_REVIEW_CAMPAIGNS,
    MAX_DIGEST_REVIEW_LIMIT,
)


class OnboardingLifecycleDigestPreviewQuerySerializer(serializers.Serializer):
    campaign_key = serializers.ChoiceField(
        choices=tuple((key, key) for key in DIGEST_REVIEW_CAMPAIGNS),
        required=False,
    )
    limit = serializers.IntegerField(
        min_value=1,
        max_value=MAX_DIGEST_REVIEW_LIMIT,
        required=False,
        default=25,
    )


class OnboardingLifecycleDigestActionSerializer(serializers.Serializer):
    action_id = serializers.CharField()
    label = serializers.CharField()
    route = serializers.CharField()
    fallback_route = serializers.CharField()
    source_type = serializers.CharField()
    source_id = serializers.CharField(required=False, allow_blank=True)
    primary_path = serializers.CharField(required=False, allow_blank=True)
    status = serializers.CharField(required=False, allow_blank=True)
    age_minutes = serializers.IntegerField(min_value=0)
    last_event_at = serializers.DateTimeField(required=False, allow_null=True)
    assigned_to_user_id = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    is_overdue = serializers.BooleanField(default=False)


class OnboardingLifecycleDigestPreviewSerializer(serializers.Serializer):
    kind = serializers.CharField()
    campaign_key = serializers.CharField()
    template_key = serializers.CharField()
    generated_at = serializers.DateTimeField(required=False, allow_null=True)
    workspace_id = serializers.CharField()
    action_count = serializers.IntegerField(min_value=0)
    omitted_action_count = serializers.IntegerField(min_value=0)
    actions = OnboardingLifecycleDigestActionSerializer(many=True)


class OnboardingLifecycleDigestSummarySerializer(serializers.Serializer):
    action_count = serializers.IntegerField(min_value=0)
    visible_action_count = serializers.IntegerField(min_value=0)
    omitted_action_count = serializers.IntegerField(min_value=0)
    overdue_count = serializers.IntegerField(min_value=0)
    assigned_count = serializers.IntegerField(min_value=0)


class OnboardingLifecycleDigestDeliveryLogSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    channel = serializers.CharField()
    status = serializers.ChoiceField(choices=NotificationDeliveryLog.STATUS_CHOICES)
    suppressed_reason = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    sent_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()


class OnboardingLifecycleDigestReviewItemSerializer(serializers.Serializer):
    source_type = serializers.ChoiceField(choices=("evaluation_log", "send_log"))
    source_id = serializers.UUIDField()
    campaign_key = serializers.CharField()
    campaign_group = serializers.CharField(required=False, allow_null=True)
    template_key = serializers.CharField(required=False, allow_null=True)
    template_version = serializers.CharField(required=False, allow_null=True)
    status = serializers.CharField()
    suppression_reason = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    user_id = serializers.UUIDField()
    workspace_id = serializers.UUIDField(required=False, allow_null=True)
    evaluated_at = serializers.DateTimeField(required=False, allow_null=True)
    queued_at = serializers.DateTimeField(required=False, allow_null=True)
    sent_at = serializers.DateTimeField(required=False, allow_null=True)
    created_at = serializers.DateTimeField()
    preview = OnboardingLifecycleDigestPreviewSerializer()
    summary = OnboardingLifecycleDigestSummarySerializer()
    delivery_logs = OnboardingLifecycleDigestDeliveryLogSerializer(many=True)

    def validate(self, attrs):
        if (
            attrs["source_type"] == "send_log"
            and attrs["status"] == OnboardingLifecycleSendLog.STATUS_SENT
            and not attrs.get("sent_at")
        ):
            raise serializers.ValidationError("Sent digest review rows need sent_at.")
        return attrs


class OnboardingLifecycleDigestReviewResultSerializer(serializers.Serializer):
    generated_at = serializers.DateTimeField()
    limit = serializers.IntegerField(min_value=1, max_value=MAX_DIGEST_REVIEW_LIMIT)
    campaign_key = serializers.CharField(required=False, allow_blank=True)
    count = serializers.IntegerField(min_value=0)
    items = OnboardingLifecycleDigestReviewItemSerializer(many=True)


class OnboardingLifecycleDigestReviewResponseSerializer(serializers.Serializer):
    status = serializers.BooleanField()
    result = OnboardingLifecycleDigestReviewResultSerializer()
