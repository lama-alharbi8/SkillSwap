from django import forms
from .models import Skill, Category

class CategoryForm(forms.ModelForm):
    
    class Meta:
        model = Category
        fields = "__all__"
        
class SkillForm(forms.ModelForm):
    
    class Meta:
        model = Skill
        fields = "__all__"
        