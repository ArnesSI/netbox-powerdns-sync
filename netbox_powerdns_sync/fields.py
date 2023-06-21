from extras.models import Tag


from django import forms
from django.db.models import Count


class MatchTagFilterField(forms.MultipleChoiceField):
    """
    A filter field for tags. Filtering is done on tag.slug
    """

    def __init__(self, *args, **kwargs):
        def get_choices():
            tags = Tag.objects.annotate(
                count=Count('extras_taggeditem_items')
            ).order_by('name')
            return [
                (str(tag.slug), '{} ({})'.format(tag.name, tag.count)) for tag in tags
            ]

        # Choices are fetched each time the form is initialized
        super().__init__(label='Match Tags', choices=get_choices, required=False, *args, **kwargs)
