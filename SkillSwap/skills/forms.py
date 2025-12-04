

from django import forms
from .models import Skill, Category, OfferedSkill, NeededSkill, SkillExchange

class CategoryForm(forms.ModelForm):
    
    class Meta:
        model = Category
        fields = "__all__"
        
class SkillForm(forms.ModelForm):
    
    class Meta:
        model = Skill
        fields = "__all__"

class OfferedSkillForm(forms.ModelForm):

    class Meta:
        model = OfferedSkill
        fields = ['skill', 'description', 'availability', 'hourly_rate_equivalent']
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the service you can provide with this skill...'
            }),
            'availability': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Weekends 9AM-5PM, Weekdays after 6PM'
            }),
            'hourly_rate_equivalent': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Estimated market rate per hour (e.g., 25.00)'
            })
        }

class NeededSkillForm(forms.ModelForm):

    class Meta:
        model = NeededSkill
        fields = ['skill', 'description', 'urgency', 'max_hourly_rate']
        widgets = {
            'skill': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the service you need...'
            }),
            'urgency': forms.Select(attrs={'class': 'form-control'}),
            'max_hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': 'Max hourly rate you can exchange (optional)'
            })
        }
        
class ProposeExchangeForm(forms.ModelForm):

    class Meta:
        model = SkillExchange
        fields = [
            'skill_from_initiator', 
            'skill_from_responder', 
            'exchange_type',
            'initiator_hours_required',
            'responder_hours_required',
            'terms', 
            'proposed_start_date', 
            'proposed_end_date'
        ]

        widgets = {
            'skill_from_initiator': forms.Select(attrs={'class': 'form-control'}),
            'skill_from_responder': forms.Select(attrs={'class': 'form-control'}),
            'exchange_type': forms.Select(attrs={'class': 'form-control'}),
            'initiator_hours_required': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0.5',
                'placeholder': 'Hours you will provide'
            }),
            'responder_hours_required': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0.5',
                'placeholder': 'Hours you expect in return'
            }),
            'terms': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Specify the terms of exchange based on hourly rates...'
            }),
            'proposed_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'proposed_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.initiator = kwargs.pop('initiator', None)
        self.responder = kwargs.pop('responder', None)
        super().__init__(*args, **kwargs)
        
        if self.initiator:
            self.fields['skill_from_initiator'].queryset = OfferedSkill.objects.filter(
                user=self.initiator, 
                is_active=True
            )
        
        if self.responder:
            self.fields['skill_from_responder'].queryset = OfferedSkill.objects.filter(
                user=self.responder, 
                is_active=True
            )
        
        if 'skill_from_initiator' in self.data and 'skill_from_responder' in self.data:
            try:
                initiator_skill_id = self.data.get('skill_from_initiator')
                responder_skill_id = self.data.get('skill_from_responder')
                
                if initiator_skill_id and responder_skill_id:
                    initiator_skill = OfferedSkill.objects.get(id=initiator_skill_id)
                    responder_skill = OfferedSkill.objects.get(id=responder_skill_id)
                    
                    rate_a = initiator_skill.hourly_rate_equivalent
                    rate_b = responder_skill.hourly_rate_equivalent
                    
                    if rate_b > 0:
                        ratio = rate_a / rate_b
                        self.fields['initiator_hours_required'].initial = 1.0
                        self.fields['responder_hours_required'].initial = round(float(ratio), 1)
            except (OfferedSkill.DoesNotExist, ValueError) as e:
                print(e)

class RespondExchangeForm(forms.ModelForm):

    class Meta:
        model = SkillExchange
        fields = ['status', 'agreed_start_date', 'agreed_end_date']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'agreed_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'agreed_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            })
        }


class ExchangeFeedbackForm(forms.Form):

    rating = forms.ChoiceField(
        choices=[(i, f'{i} stars') for i in range(1, 6)],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    feedback = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Share your experience with this exchange...'
        }),
        required=False
    )