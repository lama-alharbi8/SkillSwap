from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from .forms import CategoryForm, SkillForm, OfferedSkillForm, NeededSkillForm,ProposeExchangeForm, RespondExchangeForm, ExchangeFeedbackForm
from .models import Category, ExchangeChain, Skill, OfferedSkill, NeededSkill, SkillExchange, ChainLink
from django.db import transaction
import json
from datetime import timedelta
from django.db.models import Sum

# Create your views here.

def cat_skill_add(request):

    if request.method == 'POST':
        skill = request.POST.get('skill', '').strip()
        #nested categories
        level1 = request.POST.get('level1', '').strip()
        level2 = request.POST.get('level2', '').strip()
        level3 = request.POST.get('level3', '').strip()

        #will not save if user doesnt enter a skill
        if not skill:
            return render(request, "skills/cat_skill_add.html", {'error': 'Enter Skill Name'})

        with transaction.atomic():
            parent = None
            for lvl in (level1, level2, level3):
                if not lvl:
                    break
                #for no duplicates
                cat, created = Category.objects.get_or_create(category = lvl, parent = parent)
                #next level will be a child for this element
                parent = cat 

            skill, created = Skill.objects.get_or_create(skill = skill)

            #relation between skill and last category level
            if parent:
                skill.categories.add(parent)

        return redirect("skills:cat_skill_add")

    return render(request, "skills/cat_skill_add.html")

@login_required
def manage_skills(request):
    """User manages skills they offer and need"""
    if request.method == 'POST':
        if 'offer_skill' in request.POST:
            form = OfferedSkillForm(request.POST)
            if form.is_valid():
                offered_skill = form.save(commit=False)
                offered_skill.user = request.user
                offered_skill.save()
                messages.success(request, 'Skill offering added! Others can now request this service.')
        elif 'need_skill' in request.POST:
            form = NeededSkillForm(request.POST)
            if form.is_valid():
                needed_skill = form.save(commit=False)
                needed_skill.user = request.user
                needed_skill.save()
                messages.success(request, 'Skill need added! Browse users who offer this service.')
        return redirect('manage_skills')
    
    context = {
        'offered_skills': OfferedSkill.objects.filter(user=request.user, is_active=True),
        'needed_skills': NeededSkill.objects.filter(user=request.user, is_active=True),
        'offer_form': OfferedSkillForm(),
        'need_form': NeededSkillForm(),
        'all_skills': Skill.objects.all(),
    }
    return render(request, 'skills/manage_skills.html', context)

def calculate_fair_exchange(skill_a, skill_b, hours_a=1.0):
    """
    Calculate fair exchange based on hourly rates
    Returns: dict with hours_b, value_a, value_b, and ratio
    """
    rate_a = skill_a.hourly_rate_equivalent
    rate_b = skill_b.hourly_rate_equivalent
    
    if rate_b > 0:
        # Formula: rate_a * hours_a = rate_b * hours_b
        hours_b = (rate_a * hours_a) / rate_b
        value_a = float(rate_a * hours_a)
        value_b = float(rate_b * hours_b)
        ratio = float(rate_a / rate_b)
        
        return {
            'hours_b': round(float(hours_b), 2),
            'value_a': round(value_a, 2),
            'value_b': round(value_b, 2),
            'ratio': round(ratio, 2),
            'is_fair': abs(value_a - value_b) < 1.0  # Within $1 difference
        }
    return {'hours_b': hours_a, 'is_fair': False}

@login_required
def find_exchanges(request):
    """Find potential skill exchange partners based on hourly rates"""
    # Get current user's offerings and needs
    my_offerings = OfferedSkill.objects.filter(user=request.user, is_active=True)
    my_needs = NeededSkill.objects.filter(user=request.user, is_active=True)
    
    potential_partners = []
    
    # Method 1: Value-based matches using hourly rates
    for my_offering in my_offerings:
        # Find users who need what I offer
        users_who_need_my_skill = User.objects.filter(
            needed_skills__skill=my_offering.skill,
            needed_skills__is_active=True
        ).exclude(id=request.user.id).distinct()
        
        for user in users_who_need_my_skill:
            # Find what this user offers that I might need
            user_offerings = OfferedSkill.objects.filter(user=user, is_active=True)
            
            value_based_matches = []
            for user_offering in user_offerings:
                # Check if I need this skill
                if my_needs.filter(skill=user_offering.skill).exists():
                    # Calculate fair exchange
                    my_rate = my_offering.hourly_rate_equivalent
                    their_rate = user_offering.hourly_rate_equivalent
                    
                    if their_rate > 0:
                        # Calculate fair hours ratio
                        fair_hours_ratio = calculate_fair_exchange(my_offering, user_offering)
                        
                        value_based_matches.append({
                            'i_offer': my_offering,
                            'they_offer': user_offering,
                            'my_rate': my_rate,
                            'their_rate': their_rate,
                            'fair_ratio': fair_hours_ratio,
                            'summary': f"1 hr of your {my_offering.skill.skill} (${my_rate}/hr) = {fair_hours_ratio} hrs of their {user_offering.skill.skill} (${their_rate}/hr)"
                        })
            
            if value_based_matches:
                potential_partners.append({
                    'user': user,
                    'match_type': 'value_based',
                    'matches': value_based_matches,
                    'match_score': len(value_based_matches) * 10
                })
    
    # Method 2: Hour pool suggestions for unequal rates (ONLY IF NO VALUE-BASED MATCHES)
    if not potential_partners:
        # Suggest users with closest hourly rates
        all_users = User.objects.exclude(id=request.user.id)
        
        for user in all_users:
            user_offerings = OfferedSkill.objects.filter(user=user, is_active=True)
            
            if user_offerings.exists():
                rate_comparisons = []
                for my_offering in my_offerings:
                    for user_offering in user_offerings:
                        rate_diff = abs(float(my_offering.hourly_rate_equivalent) - float(user_offering.hourly_rate_equivalent))
                        rate_comparisons.append({
                            'my_skill': my_offering,
                            'their_skill': user_offering,
                            'rate_difference': rate_diff,
                            'fair_hours': calculate_fair_exchange(my_offering, user_offering)
                        })
                
                if rate_comparisons:
                    # Sort by closest rates (most fair)
                    rate_comparisons.sort(key=lambda x: x['rate_difference'])
                    
                    potential_partners.append({
                        'user': user,
                        'match_type': 'rate_based',
                        'matches': rate_comparisons[:3],  # Top 3 closest rate matches
                        'match_score': 100 - min([rc['rate_difference'] for rc in rate_comparisons[:3]])
                    })
    
    # Sort by match score
    potential_partners.sort(key=lambda x: x['match_score'], reverse=True)
    
    context = {
        'partners': potential_partners,
        'my_offerings': my_offerings,  # Fixed: was 'my_offering' (singular)
        'my_needs': my_needs,
    }
    return render(request, 'skills/find_exchanges.html', context)

@login_required
def propose_exchange(request, user_id, offering_id=None):
    """Propose a skill exchange with another user"""
    responder = get_object_or_404(User, id=user_id)
    
    # Get specific offering if provided
    initiator_offering = None
    if offering_id:
        initiator_offering = get_object_or_404(OfferedSkill, id=offering_id, user=request.user)
    
    if request.method == 'POST':
        form = ProposeExchangeForm(request.POST, initiator=request.user, responder=responder)
        if form.is_valid():
            exchange = form.save(commit=False)
            exchange.initiator = request.user
            exchange.responder = responder
            
            # Set timestamps
            if exchange.status == 'accepted':
                exchange.accepted_at = timezone.now()
            elif exchange.status == 'under_review':
                exchange.negotiated_at = timezone.now()
            
            exchange.save()
            messages.success(request, 'Exchange proposal sent!')
            return redirect('view_exchange', exchange_id=exchange.id)
    else:
        initial = {}
        if initiator_offering:
            initial['skill_from_initiator'] = initiator_offering
        
        form = ProposeExchangeForm(
            initial=initial,
            initiator=request.user, 
            responder=responder
        )
    
    context = {
        'form': form,
        'responder': responder,
        'responder_offerings': OfferedSkill.objects.filter(user=responder, is_active=True),
    }
    return render(request, 'skills/propose_exchange.html', context)

@login_required
def my_exchanges(request):
    """View all user's skill exchanges"""
    exchanges = SkillExchange.objects.filter(
        Q(initiator=request.user) | Q(responder=request.user)
    ).select_related(
        'initiator', 'responder', 
        'skill_from_initiator', 'skill_from_responder'
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        exchanges = exchanges.filter(status=status)
    
    # Categorize exchanges
    pending = exchanges.filter(status__in=['pending', 'under_review', 'negotiating'])
    active = exchanges.filter(status__in=['accepted', 'in_progress'])
    completed = exchanges.filter(status='completed')
    cancelled = exchanges.filter(status__in=['cancelled', 'disputed'])
    
    context = {
        'exchanges': exchanges,
        'pending': pending,
        'active': active,
        'completed': completed,
        'cancelled': cancelled,
        'status_choices': SkillExchange.STATUS_CHOICES,
    }
    return render(request, 'skills/my_exchanges.html', context)

@login_required
def view_exchange(request, exchange_id):
    """View and manage a specific skill exchange"""
    exchange = get_object_or_404(SkillExchange, id=exchange_id)
    
    # Security check
    if not exchange.is_participant(request.user):
        messages.error(request, 'Not authorized to view this exchange.')
        return redirect('my_exchanges')
    
    other_user = exchange.get_other_party(request.user)
    is_initiator = exchange.initiator == request.user
    
    if request.method == 'POST':
        if 'update_status' in request.POST:
            form = RespondExchangeForm(request.POST, instance=exchange)
            if form.is_valid():
                exchange = form.save()
                
                # Update timestamps based on status
                if exchange.status == 'accepted' and not exchange.accepted_at:
                    exchange.accepted_at = timezone.now()
                elif exchange.status == 'in_progress' and not exchange.started_at:
                    exchange.started_at = timezone.now()
                elif exchange.status == 'completed' and not exchange.completed_at:
                    exchange.completed_at = timezone.now()
                
                exchange.save()
                messages.success(request, f'Exchange status updated to {exchange.get_status_display()}')
        
        elif 'provide_feedback' in request.POST and exchange.status == 'completed':
            feedback_form = ExchangeFeedbackForm(request.POST)
            if feedback_form.is_valid():
                if is_initiator and not exchange.initiator_rating:
                    exchange.initiator_rating = feedback_form.cleaned_data['rating']
                    exchange.initiator_feedback = feedback_form.cleaned_data['feedback']
                elif not is_initiator and not exchange.responder_rating:
                    exchange.responder_rating = feedback_form.cleaned_data['rating']
                    exchange.responder_feedback = feedback_form.cleaned_data['feedback']
                
                exchange.save()
                messages.success(request, 'Thank you for your feedback!')
        
        return redirect('view_exchange', exchange_id=exchange_id)
    
    # Prepare forms
    status_form = RespondExchangeForm(instance=exchange)
    feedback_form = ExchangeFeedbackForm()
    
    # Check if user can provide feedback
    can_give_feedback = (
        exchange.status == 'completed' and
        ((is_initiator and not exchange.initiator_rating) or
         (not is_initiator and not exchange.responder_rating))
    )
    
    context = {
        'exchange': exchange,
        'other_user': other_user,
        'is_initiator': is_initiator,
        'status_form': status_form,
        'feedback_form': feedback_form,
        'can_give_feedback': can_give_feedback,
        'fairness_score': exchange.calculate_fairness_score(),
        'can_respond': (
            not is_initiator and 
            exchange.status in ['pending', 'under_review', 'negotiating']
        ),
    }
    return render(request, 'skills/view_exchange.html', context)

# ===== EXCHANGE ACTIONS =====
@login_required
def update_exchange_status(request, exchange_id, action):
    """Quick actions to update exchange status"""
    exchange = get_object_or_404(SkillExchange, id=exchange_id)
    
    if not exchange.is_participant(request.user):
        messages.error(request, 'Not authorized.')
        return redirect('my_exchanges')
    
    action_map = {
        'accept': ('accepted', 'accepted_at'),
        'start': ('in_progress', 'started_at'),
        'complete': ('completed', 'completed_at'),
        'cancel': ('cancelled', None),
        'dispute': ('disputed', None),
    }
    
    if action in action_map:
        new_status, timestamp_field = action_map[action]
        exchange.status = new_status
        
        if timestamp_field:
            setattr(exchange, timestamp_field, timezone.now())
        
        exchange.save()
        messages.success(request, f'Exchange marked as {new_status.replace("_", " ")}')
    
    return redirect('view_exchange', exchange_id=exchange_id)

@login_required
def broker_dashboard(request):
    """Broker system dashboard - suggests chain exchanges"""
    # Get user's unfulfilled needs
    my_needs = NeededSkill.objects.filter(user=request.user, is_active=True)
    my_offerings = OfferedSkill.objects.filter(user=request.user, is_active=True)
    
    broker_suggestions = []
    
    # Find chain opportunities for each unfulfilled need
    for my_need in my_needs:
        # Find users who offer what I need
        potential_providers = OfferedSkill.objects.filter(
            skill=my_need.skill,
            is_active=True
        ).exclude(user=request.user)
        
        for provider in potential_providers:
            # Now find what this provider needs
            provider_needs = NeededSkill.objects.filter(
                user=provider.user,
                is_active=True
            ).exclude(skill=my_need.skill)  # Exclude circular need
            
            for provider_need in provider_needs:
                # Find someone who can provide what the provider needs
                second_provider = OfferedSkill.objects.filter(
                    skill=provider_need.skill,
                    is_active=True
                ).exclude(user__in=[request.user, provider.user])
                
                for second_prov in second_provider:
                    # Check if second provider needs something I offer
                    second_provider_needs = NeededSkill.objects.filter(
                        user=second_prov.user,
                        is_active=True
                    )
                    
                    for second_need in second_provider_needs:
                        if second_need.skill in [o.skill for o in my_offerings]:
                            # FOUND A 3-PERSON CHAIN!
                            chain_data = {
                                'type': '3_person_chain',
                                'participants': [
                                    {
                                        'user': request.user,
                                        'gives': next(o for o in my_offerings if o.skill == second_need.skill),
                                        'receives': provider,
                                        'reason': f"You get {provider.skill.skill} from {provider.user.username}"
                                    },
                                    {
                                        'user': provider.user,
                                        'gives': provider,
                                        'receives': second_prov,
                                        'reason': f"Gets {second_prov.skill.skill} from {second_prov.user.username}"
                                    },
                                    {
                                        'user': second_prov.user,
                                        'gives': second_prov,
                                        'receives': next(o for o in my_offerings if o.skill == second_need.skill),
                                        'reason': f"Gets {next(o for o in my_offerings if o.skill == second_need.skill).skill.skill} from you"
                                    }
                                ],
                                'fairness_score': 95,
                                'summary': f"You → {provider.user.username} → {second_prov.user.username} → You"
                            }
                            broker_suggestions.append(chain_data)
    
    # If no 3-person chains, look for hour pool opportunities
    if not broker_suggestions and my_offerings.exists() and my_needs.exists():
        # Suggest hour pool: User offers hours of their skill to pool, gets hours from pool
        hour_pool_suggestion = {
            'type': 'hour_pool',
            'description': f"Offer {my_offerings[0].skill.skill} hours to the community pool, receive hours for {my_needs[0].skill.skill}",
            'estimated_wait': "1-2 weeks",
            'pool_size': "15 active users",
            'success_rate': "85%"
        }
        broker_suggestions.append(hour_pool_suggestion)
    
    context = {
        'broker_suggestions': broker_suggestions,
        'my_needs': my_needs,
        'my_offerings': my_offerings,
        'has_direct_matches': SkillExchange.objects.filter(
            Q(initiator=request.user) | Q(responder=request.user),
            status__in=['pending', 'accepted']
        ).exists()
    }
    return render(request, 'skills/broker_dashboard.html', context)

@login_required
def create_chain_proposal(request):
    """Create a chain exchange proposal from broker suggestion"""
    if request.method == 'POST':
        # Get chain data from form
        chain_name = request.POST.get('chain_name', '')
        participants_data = json.loads(request.POST.get('participants_data', '{}'))
        
        # Create the chain
        chain = ExchangeChain.objects.create(
            name=chain_name,
            status='proposed',
            total_participants=len(participants_data),
            created_by=request.user
        )
        
        # Add participants to chain
        for i, participant_data in enumerate(participants_data):
            ChainLink.objects.create(
                chain=chain,
                user_id=participant_data['user_id'],
                gives_skill_id=participant_data['gives_skill_id'],
                receives_skill_id=participant_data['receives_skill_id'],
                hours_given=participant_data.get('hours_given', 1.0),
                hours_received=participant_data.get('hours_received', 1.0),
                position=i,
                status='pending'
            )
        
        # Notify all participants
        for link in chain.chain_links.all():
            # Create notification for each user
            messages.success(
                request, 
                f"Chain proposal sent to {link.user.username}"
            )
        
        return redirect('view_chain', chain_id=chain.id)
    
    return redirect('broker_dashboard')

@login_required
def view_chain(request, chain_id):
    """View a chain exchange proposal"""
    chain = get_object_or_404(ExchangeChain, id=chain_id)
    
    # Check if user is part of this chain
    user_link = ChainLink.objects.filter(chain=chain, user=request.user).first()
    if not user_link and not request.user.is_staff:
        messages.error(request, "You are not part of this chain.")
        return redirect('broker_dashboard')
    
    # Get chain details
    chain_links = chain.chain_links.all().order_by('position')
    chain_summary = chain.get_chain_summary()
    fairness_score = chain.calculate_fairness()
    
    # Determine user's position and neighbors
    my_position = user_link.position if user_link else None
    next_user = user_link.get_next_in_chain() if user_link else None
    prev_user = user_link.get_previous_in_chain() if user_link else None
    
    context = {
        'chain': chain,
        'chain_links': chain_links,
        'chain_summary': chain_summary,
        'fairness_score': fairness_score,
        'user_link': user_link,
        'my_position': my_position,
        'next_user': next_user,
        'prev_user': prev_user,
        'can_accept': user_link and user_link.status == 'pending',
        'is_complete_chain': chain_links.count() >= 3,
    }
    return render(request, 'skills/view_chain.html', context)

@login_required
def respond_to_chain(request, chain_id, response):
    """User responds to chain invitation (accept/reject)"""
    chain = get_object_or_404(ExchangeChain, id=chain_id)
    user_link = get_object_or_404(ChainLink, chain=chain, user=request.user)
    
    if response in ['accept', 'reject']:
        user_link.status = 'accepted' if response == 'accept' else 'rejected'
        user_link.responded_at = timezone.now()
        user_link.save()
        
        # Check if all have accepted
        all_accepted = not chain.chain_links.filter(status__in=['pending', 'rejected']).exists()
        if all_accepted:
            chain.status = 'accepted'
            chain.accepted_at = timezone.now()
            chain.save()
            
            # Create individual SkillExchange records for each link
            for link in chain.chain_links.all():
                SkillExchange.objects.create(
                    initiator=link.user,
                    responder=link.get_next_in_chain().user,
                    skill_from_initiator=link.gives_skill,
                    skill_from_responder=link.get_next_in_chain().gives_skill,
                    exchange_type='direct',
                    status='accepted',
                    terms=f"Part of chain exchange #{chain.id}",
                    initiator_hours_required=link.hours_given,
                    responder_hours_required=link.hours_received,
                    agreed_start_date=timezone.now().date(),
                    agreed_end_date=(timezone.now() + timedelta(days=30)).date()
                )
        
        messages.success(request, f"You {response}ed the chain proposal.")
    
    return redirect('view_chain', chain_id=chain_id)

@login_required
def hour_pool(request):
    """Hour pool system - users contribute hours, withdraw hours"""
    # Get user's pool balance
    pool_balance = {
        'hours_contributed': 0,
        'hours_withdrawn': 0,
        'available_hours': 0,
        'pending_contributions': [],
        'pending_requests': []
    }
    
    # Find available skills in pool
    available_in_pool = OfferedSkill.objects.filter(
        is_active=True
    ).exclude(
        user=request.user
    ).annotate(
        pool_hours=Sum('userservice__pool_hours')
    ).filter(
        pool_hours__gt=0
    )
    
    # User's contributions to pool
    user_contributions = OfferedSkill.objects.filter(
        user=request.user,
        is_active=True
    )
    
    context = {
        'pool_balance': pool_balance,
        'available_in_pool': available_in_pool,
        'user_contributions': user_contributions,
        'pool_stats': {
            'total_users': User.objects.count(),
            'total_hours': 150,  # Would calculate from DB
            'successful_exchanges': 42,
        }
    }
    return render(request, 'skills/hour_pool.html', context)

