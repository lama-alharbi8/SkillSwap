from django import forms
from .models import Category, Skill

class UserRegisterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset = Category.objects.all(),
        required=True,
        label="Category"
    )
    skill = forms.ModelChoiceField(
        queryset=Skill.objects.none(),
        required=True,
        label="Skill"
    )

    def __init__(self, *args, **kwargs):
        category_id = kwargs.pop('category_id', None) 
        super().__init__(*args, **kwargs)
        if category_id:
            self.fields['skill'].queryset = Skill.objects.filter(categories__id=category_id)
