from django import forms

from .models import Tag

COLORS_CHOICES = [
    ('#87CEEB', 'Голубой'),
    ('#D8BFD8', 'Лавандовый'),
    ('#FFDAB9', 'Персиковый'),
    ('#FFA07A', 'Лососевый'),
    ('#3CB371', 'Нежно зеленый'),
    ('#F08080', 'Коралловый'),
]


class TagAdminForm(forms.ModelForm):
    color = forms.ChoiceField(
        required=True,
        widget=forms.RadioSelect,
        choices=COLORS_CHOICES,
    )

    class Meta:
        model = Tag
        fields = '__all__'
