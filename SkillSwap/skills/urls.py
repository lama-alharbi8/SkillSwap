from django.urls import path
from . import views

app_name = "skills"

urlpatterns = [
    path("add/category/skill", views.cat_skill_add, name="cat_skill_add"),
    path('manage/', views.manage_skills, name='manage_skills'),
    path('find-exchanges/', views.find_exchanges, name='find_exchanges'),
    path('exchange/propose/<int:user_id>/', views.propose_exchange, name='propose_exchange'),
    path('exchange/propose/<int:user_id>/<int:offering_id>/', views.propose_exchange, name='propose_exchange_with_offering'),
    path('exchanges/', views.my_exchanges, name='my_exchanges'),
    path('exchange/<int:exchange_id>/', views.view_exchange, name='view_exchange'),
    path('exchange/<int:exchange_id>/<str:action>/', views.update_exchange_status, name='update_exchange_status'),
    path('broker/', views.broker_dashboard, name='broker_dashboard'),
    path('broker/create-chain/', views.create_chain_proposal, name='create_chain'),
    path('chain/<int:chain_id>/', views.view_chain, name='view_chain'),
    path('chain/<int:chain_id>/<str:response>/', views.respond_to_chain, name='respond_to_chain'),
    path('hour-pool/', views.hour_pool, name='hour_pool'),

] 