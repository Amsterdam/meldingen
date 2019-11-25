from django.conf import settings
from django.db.models import QuerySet


class SignalQuerySet(QuerySet):
    def filter_for_user(self, user):
        if settings.FEATURE_FLAGS.get('PERMISSION_DEPARTMENTS', False):
            if not user.is_superuser and not user.has_perm('signals.sia_can_view_all_categories'):
                # We are not a superuser and we do not have the "show all categories" permission
                return self.filter(
                    category_assignment__category__departments__in=list(
                        user.profile.departments.values_list('pk', flat=True)
                    )
                )

        return self.all()
