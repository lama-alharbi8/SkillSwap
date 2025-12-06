from django import forms
from django.contrib.auth.models import User
from .models import (
    Skill, OfferedSkill, NeededSkill, 
    SkillExchange, ExchangeChain, ChainLink
)
from django.core.exceptions import ValidationError


class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = "__all__"


class OfferSkillForm(forms.ModelForm):
    class Meta:
        model = OfferedSkill
        fields = ['skill', 'description', 'availability', 'hourly_rate_equivalent']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'availability': forms.TextInput(attrs={'placeholder': 'e.g., Weekends, Evenings'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
           
            already_offering = user.offered_skills.values_list('skill_id', flat=True)
            available_skills = Skill.objects.exclude(id__in=already_offering)
            
            self.fields['skill'].queryset = available_skills
            self.fields['skill'].empty_label = "Select a skill to offer"
            

            if already_offering.exists():
                self.fields['skill'].help_text = f"You're already offering {already_offering.count()} skill(s)"
        else:
            self.fields['skill'].queryset = Skill.objects.none()


class NeedSkillForm(forms.ModelForm):
    class Meta:
        model = NeededSkill
        fields = ['skill', 'description', 'urgency', 'max_hourly_rate']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'max_hourly_rate': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
           
            already_needing = user.needed_skills.values_list('skill_id', flat=True)
            available_skills = Skill.objects.exclude(id__in=already_needing)
            
            self.fields['skill'].queryset = available_skills
            self.fields['skill'].empty_label = "Select a skill you need"
            
            if already_needing.exists():
                self.fields['skill'].help_text = f"You're already requesting {already_needing.count()} skill(s)"
        else:
           
            self.fields['skill'].queryset = Skill.objects.all()


class ProposeExchangeForm(forms.ModelForm):
    """Form for proposing an exchange to someone who needs a skill"""
    class Meta:
        model = SkillExchange
        fields = ['skill_from_responder', 'terms', 'proposed_start_date', 'proposed_end_date']
        widgets = {
            'terms': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe the exchange details, schedule, expectations...'
            }),
            'proposed_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'proposed_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.responder = kwargs.pop('responder', None)  
        self.needed_skill = kwargs.pop('needed_skill', None)  
        super().__init__(*args, **kwargs)
        
        if self.responder and self.needed_skill:
            
            self.fields['skill_from_responder'].queryset = OfferedSkill.objects.filter(
                user=self.responder,
                is_active=True
            )
            self.fields['skill_from_responder'].label = "Select the skill you'll offer"
            self.fields['skill_from_responder'].help_text = "Choose which of your skills to exchange"


class ExchangeNegotiationForm(forms.ModelForm):
    initiator_hours_required = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    responder_hours_required = forms.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'})
    )
    
    class Meta:
        model = SkillExchange
        fields = ['terms', 'initiator_hours_required', 'responder_hours_required']
        widgets = {
            'terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        initiator_hours = cleaned_data.get('initiator_hours_required')
        responder_hours = cleaned_data.get('responder_hours_required')
        
        if initiator_hours and responder_hours:
            if initiator_hours > 100 or responder_hours > 100:
                raise ValidationError("Hours cannot exceed 100 per exchange.")
        
        return cleaned_data


class ExchangeProposalForm(forms.ModelForm):
    class Meta:
        model = ExchangeChain
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Design-Development-Writing Chain'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the purpose of this exchange chain...'
            }),
        }


class ChainLinkForm(forms.ModelForm):
    class Meta:
        model = ChainLink
        fields = ['gives_skill', 'receives_skill', 'hours_given', 'hours_received']
        widgets = {
            'gives_skill': forms.Select(attrs={'class': 'form-control'}),
            'receives_skill': forms.Select(attrs={'class': 'form-control'}),
            'hours_given': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'hours_received': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }
    
    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
           
            self.fields['gives_skill'].queryset = OfferedSkill.objects.filter(
                user=user, is_active=True
            )


class UserSearchForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username...'
        })
    )


class FilterSkillsForm(forms.Form):
    min_rate = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min rate',
            'step': '0.01'
        })
    )
    max_rate = forms.DecimalField(
        required=False,
        max_digits=7,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max rate',
            'step': '0.01'
        })
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search skills...'
        })
    )


class RatingForm(forms.Form):
    RATING_CHOICES = [
        (5, '⭐⭐⭐⭐⭐ - Excellent'),
        (4, '⭐⭐⭐⭐ - Good'),
        (3, '⭐⭐⭐ - Average'),
        (2, '⭐⭐ - Poor'),
        (1, '⭐ - Very Poor'),
    ]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect
    )
    feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Optional feedback...'
        })
    )