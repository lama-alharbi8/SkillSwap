from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Create your models here.

class Category(models.Model):
    
    category = models.CharField(max_length = 128, unique = True)
    
    parent = models.ForeignKey(
        'self', 
        null = True, 
        blank = True, 
        related_name = 'children', 
        on_delete = models.CASCADE
    )
    
    def __str__(self) -> str:
        return self.category
    
    def get_full_path(self):
        full_path = [self.category]
        k = self.parent
        while k is not None:
            full_path.append(k.category)
            k = k.parent
        return ' > '.join(full_path[::-1])

class Skill(models.Model):

    skill = models.CharField(max_length = 128, unique = True)
    
    def __str__(self) -> str:
        return self.skill
    
class OfferedSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offered_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='offered_by_users')
    description = models.TextField(blank=True, help_text='Describe the service you can provide')
    availability = models.CharField(max_length=200, blank=True, help_text='e.g., Weekends, Evenings')
    hourly_rate_equivalent = models.DecimalField(
        max_digits=7,
        decimal_places=2,  
        default=25.00,
        validators=[MinValueValidator(1)],  
        help_text="Estimated market rate per hour (for fair exchange calculation)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ['user', 'skill']
        verbose_name = "Offered Skill"
        verbose_name_plural = "Offered Skills"

    def __str__(self):
        return f'{self.user.username} offers: {self.skill.skill} (${self.hourly_rate_equivalent}/hr)'
    
    def get_value_per_hour(self):
        return float(self.hourly_rate_equivalent)


class NeededSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='needed_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='needed_by_users')
    description = models.TextField(blank=True, help_text="Describe what service you need")
    urgency = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low - No rush'),
            ('medium', 'Medium - Within a month'),
            ('high', 'High - As soon as possible'),
        ],
        default='medium'
    )
    max_hourly_rate = models.DecimalField(
        max_digits=7,
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Maximum hourly rate you're willing to exchange for this service"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['user', 'skill']
        verbose_name = "Needed Skill"
        verbose_name_plural = "Needed Skills"
    
    def __str__(self):
        return f"{self.user.username} needs: {self.skill.skill}"

class SkillExchange(models.Model):
    EXCHANGE_TYPES = [
        ('direct', 'Direct Exchange - Equal hourly value'),
        ('hourly', 'Hour Exchange - Hours for Hours'),
        ('value', 'Value Exchange - Based on hourly rates'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('under_review', 'Under Review'),
        ('negotiating', 'Negotiating Terms'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('disputed', 'Disputed'),
    ]

    initiator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='initiated_exchanges')
    responder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='responded_exchanges')

    skill_from_initiator = models.ForeignKey(OfferedSkill, on_delete=models.CASCADE, related_name='exchanges_as_offer')
    skill_from_responder = models.ForeignKey(OfferedSkill, on_delete=models.CASCADE, related_name='exchanges_as_response')

    exchange_type = models.CharField(max_length=20, choices=EXCHANGE_TYPES, default='value')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    initiator_hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    responder_hourly_rate = models.DecimalField(max_digits=7, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    calculated_ratio = models.DecimalField(max_digits=15, decimal_places=5, default=1.0, help_text='Ratio of hours needed for fair exchange')

    initiator_hours_required = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, validators=[MinValueValidator(0.1)])
    responder_hours_required = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, validators=[MinValueValidator(0.1)])
    total_value = models.DecimalField(max_digits=9, decimal_places=2, default=0, help_text="Total value of exchange in $ equivalent")
    
    is_balanced = models.BooleanField(default=False, help_text="Whether the exchange is financially balanced")
    imbalance_amount = models.DecimalField(max_digits=9, decimal_places=2, default=0, help_text="Monetary value difference if not perfectly balanced")
    
    terms = models.TextField(blank=True, help_text="Specific terms and conditions")

    proposed_start_date = models.DateField(null=True, blank=True)
    proposed_end_date = models.DateField(null=True, blank=True)
    agreed_start_date = models.DateField(null=True, blank=True)
    agreed_end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    negotiated_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    initiator_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    responder_rating = models.IntegerField(null=True, blank=True, choices=[(i, i) for i in range(1, 6)])
    initiator_feedback = models.TextField(blank=True)
    responder_feedback = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Skill Exchange"
        verbose_name_plural = "Skill Exchanges"

    def __str__(self):
        return f"Exchange #{self.id}: {self.initiator.username} ↔ {self.responder.username}"

    def clean(self):


        if self.initiator == self.responder:
            raise ValidationError("Cannot exchange with yourself")
        

        if hasattr(self, 'skill_from_initiator') and self.skill_from_initiator:
            if self.skill_from_initiator.user != self.initiator:
                raise ValidationError("Initiator must own the offered skill")
                
        if hasattr(self, 'skill_from_responder') and self.skill_from_responder:
            if self.skill_from_responder.user != self.responder:
                raise ValidationError("Responder must own the offered skill")

    def get_exchange_summary(self):
        return f'{self.skill_from_initiator.skill.skill} ↔ {self.skill_from_responder.skill.skill}'
    
    def calculate_fair_exchange(self):
  
        try:
          
            rate_a = float(self.skill_from_initiator.hourly_rate_equivalent)
            rate_b = float(self.skill_from_responder.hourly_rate_equivalent)
            
          
            self.initiator_hourly_rate = rate_a
            self.responder_hourly_rate = rate_b
            
          
            if rate_a <= 0 or rate_b <= 0:
             
                self.initiator_hours_required = 1.0
                self.responder_hours_required = 1.0
                self.calculated_ratio = 1.0
                self.total_value = 0
                self.is_balanced = False
                self.imbalance_amount = 0
                return None
            
           
            ratio = rate_a / rate_b
            self.calculated_ratio = ratio
            
      
            if ratio >= 1:
            
                self.initiator_hours_required = 1.0
                self.responder_hours_required = round(ratio, 2)  
            else:
             
                self.responder_hours_required = 1.0
                self.initiator_hours_required = round(1 / ratio, 2)  

            initiator_value = rate_a * float(self.initiator_hours_required)
            responder_value = rate_b * float(self.responder_hours_required)
            
   
            self.total_value = (initiator_value + responder_value) / 2
            
     
            value_difference = abs(initiator_value - responder_value)
            self.imbalance_amount = value_difference
            
        
            if self.total_value > 0:
                tolerance = self.total_value * 0.01  
                self.is_balanced = value_difference <= tolerance
            else:
                self.is_balanced = value_difference <= 0.01 
            
            return {
                'ratio': ratio,
                'initiator_hours': float(self.initiator_hours_required),
                'responder_hours': float(self.responder_hours_required),
                'initiator_value': initiator_value,
                'responder_value': responder_value,
                'total_value': float(self.total_value),
                'is_balanced': self.is_balanced,
                'imbalance': float(self.imbalance_amount)
            }
        except (AttributeError, ValueError, TypeError) as e:
          
            self.initiator_hours_required = 1.0
            self.responder_hours_required = 1.0
            self.calculated_ratio = 1.0
            self.total_value = 0
            self.is_balanced = False
            self.imbalance_amount = 0
            return None
    
    def save(self, *args, **kwargs):
        
      
        skip_calculation = kwargs.pop('skip_calculation', False)
        
      
        if (not skip_calculation and self.skill_from_initiator_id and 
            self.skill_from_responder_id):
            self.calculate_fair_exchange()
        
        try:
            self.full_clean()
        except ValidationError as e:
            raise e
        
        super().save(*args, **kwargs)
    
    def is_participant(self, user):
        return user in [self.initiator, self.responder]
    
    def get_fairness_score(self):
      
        try:
        
            initiator_rate = float(self.initiator_hourly_rate)
            responder_rate = float(self.responder_hourly_rate)
            initiator_hours = float(self.initiator_hours_required)
            responder_hours = float(self.responder_hours_required)
            
            if initiator_rate <= 0 or responder_rate <= 0 or initiator_hours <= 0 or responder_hours <= 0:
                return 0
            
 
            initiator_value_given = initiator_rate * initiator_hours
            responder_value_given = responder_rate * responder_hours
            
     
            max_value = max(initiator_value_given, responder_value_given)
            if max_value > 0:
                fairness = min(initiator_value_given, responder_value_given) / max_value
                return round(fairness * 100, 1)
        except (ValueError, TypeError):
            pass
        
        
        return 0
    
    def get_value_imbalance(self):
      
        try:
            initiator_value = float(self.initiator_hourly_rate) * float(self.initiator_hours_required)
            responder_value = float(self.responder_hourly_rate) * float(self.responder_hours_required)
            return abs(initiator_value - responder_value)
        except (ValueError, TypeError):
            return 0
    
    def suggest_adjustment(self):
    
        try:
            initiator_rate = float(self.initiator_hourly_rate)
            responder_rate = float(self.responder_hourly_rate)
            
            if initiator_rate <= 0 or responder_rate <= 0:
                return None
            
       
            perfect_ratio = initiator_rate / responder_rate
            
            initiator_hours = float(self.initiator_hours_required)
            responder_hours = float(self.responder_hours_required)
            current_ratio = initiator_hours / responder_hours if responder_hours > 0 else 0
            
          
            if perfect_ratio > 0 and abs(current_ratio - perfect_ratio) / perfect_ratio > 0.05:
                if perfect_ratio >= 1:
                    suggested_initiator_hours = 1.0
                    suggested_responder_hours = round(perfect_ratio, 1)
                else:
                    suggested_responder_hours = 1.0
                    suggested_initiator_hours = round(1 / perfect_ratio, 1)
                
                return {
                    'perfect_ratio': round(perfect_ratio, 2),
                    'adjustment_needed': True,
                    'suggested_initiator_hours': suggested_initiator_hours,
                    'suggested_responder_hours': suggested_responder_hours,
                    'current_fairness_score': self.get_fairness_score()
                }
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        
        return {'adjustment_needed': False, 'fairness_score': self.get_fairness_score()}
    
    def get_detailed_fairness_report(self):

        try:
            initiator_value = float(self.initiator_hourly_rate) * float(self.initiator_hours_required)
            responder_value = float(self.responder_hourly_rate) * float(self.responder_hours_required)
            responder_rate = float(self.responder_hourly_rate)
            responder_hours = float(self.responder_hours_required)
            
            hourly_rate_ratio = float(self.initiator_hourly_rate) / responder_rate if responder_rate > 0 else 0
            hours_ratio = float(self.initiator_hours_required) / responder_hours if responder_hours > 0 else 0
            
            return {
                'fairness_score': self.get_fairness_score(),
                'initiator_value': initiator_value,
                'responder_value': responder_value,
                'value_difference': abs(initiator_value - responder_value),
                'hourly_rate_ratio': hourly_rate_ratio,
                'hours_ratio': hours_ratio,
                'is_balanced': self.get_fairness_score() >= 95,  # 95% threshold
                'calculated_ratio': float(self.calculated_ratio),
                'total_value': float(self.total_value)
            }
        except (ValueError, TypeError, ZeroDivisionError):
            return {
                'fairness_score': 0,
                'initiator_value': 0,
                'responder_value': 0,
                'value_difference': 0,
                'hourly_rate_ratio': 0,
                'hours_ratio': 0,
                'is_balanced': False,
                'calculated_ratio': 0,
                'total_value': 0
            }
    
    def get_other_party(self, user):
  
        if user == self.initiator:
            return self.responder
        elif user == self.responder:
            return self.initiator
        return None

    
class ExchangeChain(models.Model):

    STATUS_CHOICES = [
        ('forming', 'Forming - Looking for participants'),
        ('proposed', 'Proposed - Chain identified'),
        ('pending', 'Pending - All parties reviewing'),
        ('accepted', 'Accepted - All parties agreed'),
        ('in_progress', 'In Progress - Chain active'),
        ('completed', 'Completed - All exchanges done'),
        ('cancelled', 'Cancelled - Chain abandoned'),
    ]
    
    name = models.CharField(max_length=100, blank=True, help_text="Optional chain name")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='forming')
    description = models.TextField(blank=True)
    
    
    total_participants = models.IntegerField(default=0)
    total_hours = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='created_chains'
    )
    

    created_at = models.DateTimeField(auto_now_add=True)
    proposed_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Exchange Chain"
        verbose_name_plural = "Exchange Chains"
    
    def __str__(self):
        return f"Chain #{self.id}: {self.name or 'Unnamed Chain'}"
    
    def get_chain_summary(self):
       
        links = self.chain_links.all().order_by('position')
        if links.exists():
            users = [link.user.username for link in links]
            return " → ".join(users) + f" → {users[0]}" 
        return "Empty Chain"
    
    def calculate_fairness(self):
       
        links = self.chain_links.all()
        if links.count() < 2:
            return 100
        
    
        hours_given = sum([float(link.hours_given) for link in links])
        hours_received = sum([float(link.hours_received) for link in links])
        

        value_given = 0
        value_received = 0
        
        for link in links:
            if link.gives_skill:
                value_given += float(link.gives_skill.hourly_rate_equivalent) * float(link.hours_given)
            if link.receives_skill:
                value_received += float(link.receives_skill.hourly_rate_equivalent) * float(link.hours_received)
        
        if value_received > 0:
            fairness_score = min(value_given, value_received) / max(value_given, value_received) * 100
            return round(fairness_score, 1)
        
     
        if hours_received > 0:
            return round(min(hours_given, hours_received) / max(hours_given, hours_received) * 100, 1)
        
        return 0
    
    def update_chain_metrics(self):
       
        links = self.chain_links.all()
        self.total_participants = links.count()
        
        total_hours = sum([float(link.hours_given) for link in links])
        self.total_hours = total_hours
        self.save(update_fields=['total_participants', 'total_hours'])
    
class ChainLink(models.Model):

    chain = models.ForeignKey(ExchangeChain, on_delete=models.CASCADE, related_name='chain_links')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chain_participations')

    gives_skill = models.ForeignKey(OfferedSkill, on_delete=models.CASCADE, related_name='given_in_chains')
    receives_skill = models.ForeignKey(OfferedSkill, on_delete=models.CASCADE, related_name='received_in_chains')
    

    hours_given = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, validators=[MinValueValidator(0.1)])
    hours_received = models.DecimalField(max_digits=5, decimal_places=2, default=1.0, validators=[MinValueValidator(0.1)])
    

    position = models.IntegerField(default=0)
    

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending - Not yet reviewed'),
            ('reviewing', 'Reviewing - Considering proposal'),
            ('accepted', 'Accepted - Agreed to participate'),
            ('rejected', 'Rejected - Declined to participate'),
        ],
        default='pending'
    )
    

    joined_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['chain', 'position']
        unique_together = [
            ['chain', 'user'],
            ['chain', 'position']
        ]
    
    def __str__(self):
        return f"{self.user.username} in Chain #{self.chain.id} (Position {self.position})"
    
    def get_value_given(self):
    
        if self.gives_skill:
            return float(self.gives_skill.hourly_rate_equivalent) * float(self.hours_given)
        return 0
    
    def get_value_received(self):
  
        if self.receives_skill:
            return float(self.receives_skill.hourly_rate_equivalent) * float(self.hours_received)
        return 0
    
    def get_fairness_for_user(self):
    
        value_given = self.get_value_given()
        value_received = self.get_value_received()
        
        if max(value_given, value_received) > 0:
            fairness = min(value_given, value_received) / max(value_given, value_received) * 100
            return round(fairness, 1)
        return 0
    
    def get_next_in_chain(self):
    
        try:
            return ChainLink.objects.get(chain=self.chain, position=self.position + 1)
        except ChainLink.DoesNotExist:
  
            return ChainLink.objects.filter(chain=self.chain).order_by('position').first()
    
    def get_previous_in_chain(self):

        try:
            return ChainLink.objects.get(chain=self.chain, position=self.position - 1)
        except ChainLink.DoesNotExist:

            return ChainLink.objects.filter(chain=self.chain).order_by('-position').first()
    
    def save(self, *args, **kwargs):

        super().save(*args, **kwargs)
        self.chain.update_chain_metrics()


class BrokerProposal(models.Model):

    PROPOSAL_TYPES = [
        ('chain_3', '3-Person Chain (A→B→C→A)'),
        ('chain_4', '4-Person Chain (A→B→C→D→A)'),
        ('hour_pool', 'Hour Pool Exchange'),
        ('future_credit', 'Future Credit Exchange'),
    ]
    
    proposal_type = models.CharField(max_length=20, choices=PROPOSAL_TYPES, default='chain_3')
    title = models.CharField(max_length=200)
    description = models.TextField()
    

    participants_data = models.JSONField(default=dict, help_text="Structured data about proposed exchanges")
    

    status = models.CharField(
        max_length=20,
        choices=[
            ('generated', 'Generated - By system'),
            ('proposed', 'Proposed - Sent to users'),
            ('accepted', 'Accepted - All agreed'),
            ('rejected', 'Rejected - Not viable'),
            ('converted', 'Converted - To actual exchanges'),
        ],
        default='generated'
    )
    

    fairness_score = models.IntegerField(default=0, help_text="0-100 score of how fair the exchange is")
    efficiency_score = models.IntegerField(default=0, help_text="0-100 score of chain efficiency")
    

    created_at = models.DateTimeField(auto_now_add=True)
    proposed_to_users_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-fairness_score', '-created_at']
    
    def __str__(self):
        return f"Broker Proposal: {self.title}"
    
    def propose_to_users(self):

        self.status = 'proposed'
        self.proposed_to_users_at = timezone.now()
        self.save()
    
    def calculate_proposal_fairness(self):

        if 'participants' in self.participants_data:
            total_value_given = 0
            total_value_received = 0
            
            for participant in self.participants_data['participants']:

                if 'gives_value' in participant:
                    total_value_given += participant['gives_value']
                if 'receives_value' in participant:
                    total_value_received += participant['receives_value']
            
            if max(total_value_given, total_value_received) > 0:
                self.fairness_score = int(min(total_value_given, total_value_received) / 
                                          max(total_value_given, total_value_received) * 100)
                self.save()

class Notification(models.Model):

    NOTIFICATION_TYPES = [
        ('exchange_proposed', 'Exchange Proposed'),
        ('exchange_accepted', 'Exchange Accepted'),
        ('exchange_rejected', 'Exchange Rejected'),
        ('exchange_completed', 'Exchange Completed'),
        ('exchange_cancelled', 'Exchange Cancelled'),
        ('rating_received', 'Rating Received'),
        ('message', 'Message'),
        ('system', 'System Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    

    is_read = models.BooleanField(default=False)
    

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.title}"
    
    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()
    
    @property
    def time_since(self):
        """Get human-readable time since notification"""
        now = timezone.now()
        diff = now - self.created_at
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"