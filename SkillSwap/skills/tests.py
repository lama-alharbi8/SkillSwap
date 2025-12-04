from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from django.utils import timezone
from .models import Skill, Category, OfferedSkill, NeededSkill, SkillExchange

# Create your tests here.

class FairnessCalculationTestCase(TestCase):
    """
    Test suite for skill exchange fairness calculations
    """
    
    def setUp(self):
        """
        Create test data that will be available in every test method
        """
        print("\n" + "="*60)
        print("Setting up test data...")
        print("="*60)
        
        # Create test users
        self.designer = User.objects.create_user(
            username='designer_john',
            email='john@example.com',
            password='testpass123'
        )
        self.developer = User.objects.create_user(
            username='dev_sarah',
            email='sarah@example.com',
            password='testpass123'
        )
        self.writer = User.objects.create_user(
            username='writer_mike',
            email='mike@example.com',
            password='testpass123'
        )
        
        # Create categories
        self.design_category = Category.objects.create(category='Design')
        self.tech_category = Category.objects.create(category='Technology')
        
        # Create skills
        self.graphic_design = Skill.objects.create(skill='Graphic Design')
        self.graphic_design.categories.add(self.design_category)
        
        self.web_dev = Skill.objects.create(skill='Web Development')
        self.web_dev.categories.add(self.tech_category)
        
        self.content_writing = Skill.objects.create(skill='Content Writing')
        
        # Create offered skills with different hourly rates
        print("Creating offered skills...")
        self.design_offer = OfferedSkill.objects.create(
            user=self.designer,
            skill=self.graphic_design,
            description='Professional logo and brand design',
            hourly_rate_equivalent=50.00,  # $50/hour
            is_active=True
        )
        print(f"  ✓ {self.designer.username}: ${self.design_offer.hourly_rate_equivalent}/hr")
        
        self.dev_offer = OfferedSkill.objects.create(
            user=self.developer,
            skill=self.web_dev,
            description='Full-stack web development',
            hourly_rate_equivalent=40.00,  # $40/hour
            is_active=True
        )
        print(f"  ✓ {self.developer.username}: ${self.dev_offer.hourly_rate_equivalent}/hr")
        
        self.writing_offer = OfferedSkill.objects.create(
            user=self.writer,
            skill=self.content_writing,
            description='SEO-optimized content writing',
            hourly_rate_equivalent=25.00,  # $25/hour
            is_active=True
        )
        print(f"  ✓ {self.writer.username}: ${self.writing_offer.hourly_rate_equivalent}/hr")
        
        print("✓ Test data setup complete!")
    
    def test_1_basic_fair_exchange(self):
        """
        TEST 1: Designer ($50/hr) exchanges with Developer ($40/hr)
        Expected: Designer works 1 hour, Developer works 1.25 hours
        Calculation: 50/40 = 1.25
        """
        print("\n" + "="*60)
        print("TEST 1: Basic Fair Exchange")
        print("Designer ($50/hr) ↔ Developer ($40/hr)")
        print("="*60)
        
        # Create the exchange
        exchange = SkillExchange.objects.create(
            initiator=self.designer,
            responder=self.developer,
            skill_from_initiator=self.design_offer,
            skill_from_responder=self.dev_offer,
            terms="Design logo for portfolio website"
        )
        
        # Display results
        print(f"\n💰 Hourly Rates:")
        print(f"  {exchange.initiator.username}: ${exchange.initiator_hourly_rate}/hr")
        print(f"  {exchange.responder.username}: ${exchange.responder_hourly_rate}/hr")
        
        print(f"\n⏰ Calculated Hours:")
        print(f"  {exchange.initiator.username}: {exchange.initiator_hours_required} hours")
        print(f"  {exchange.responder.username}: {exchange.responder_hours_required} hours")
        
        print(f"\n📊 Fairness Metrics:")
        print(f"  Fairness Score: {exchange.get_fairness_score()}%")
        print(f"  Is Balanced: {exchange.is_balanced}")
        print(f"  Total Value: ${exchange.total_value}")
        
        # Manual calculation for verification
        expected_ratio = 50.00 / 40.00  # Should be 1.25
        expected_hours_dev = expected_ratio  # Should be 1.25 hours
        
        print(f"\n🧮 Manual Verification:")
        print(f"  Expected Ratio: {expected_ratio}")
        print(f"  Expected {exchange.responder.username} hours: {expected_hours_dev}")
        
        # Assertions - these will PASS or FAIL the test
        self.assertEqual(float(exchange.initiator_hourly_rate), 50.00)
        self.assertEqual(float(exchange.responder_hourly_rate), 40.00)
        self.assertEqual(float(exchange.initiator_hours_required), 1.0)
        self.assertAlmostEqual(float(exchange.responder_hours_required), expected_hours_dev, places=1)
        self.assertEqual(exchange.get_fairness_score(), 100.0)
        self.assertTrue(exchange.is_balanced)
        
        print("\n✅ TEST 1 PASSED: Basic fair exchange calculated correctly!")
        return True
    
    def test_2_reverse_value_exchange(self):
        """
        TEST 2: Writer ($25/hr) exchanges with Designer ($50/hr)
        Expected: Writer works 2 hours, Designer works 1 hour
        Calculation: 50/25 = 2.0
        """
        print("\n" + "="*60)
        print("TEST 2: Reverse Value Exchange")
        print("Writer ($25/hr) ↔ Designer ($50/hr)")
        print("="*60)
        
        exchange = SkillExchange.objects.create(
            initiator=self.writer,  # Writer initiates
            responder=self.designer,
            skill_from_initiator=self.writing_offer,
            skill_from_responder=self.design_offer,
            terms="Write blog posts for logo design"
        )
        
        print(f"\n💰 Hourly Rates:")
        print(f"  {exchange.initiator.username}: ${exchange.initiator_hourly_rate}/hr")
        print(f"  {exchange.responder.username}: ${exchange.responder_hourly_rate}/hr")
        
        print(f"\n⏰ Calculated Hours:")
        print(f"  {exchange.initiator.username}: {exchange.initiator_hours_required} hours")
        print(f"  {exchange.responder.username}: {exchange.responder_hours_required} hours")
        
        # Manual verification
        expected_ratio = 25.00 / 50.00  # Should be 0.5
        expected_hours_writer = 2.0  # Writer should work 2 hours
        expected_hours_designer = 1.0  # Designer should work 1 hour
        
        print(f"\n🧮 Expected:")
        print(f"  {exchange.initiator.username} (cheaper): {expected_hours_writer} hours")
        print(f"  {exchange.responder.username} (expensive): {expected_hours_designer} hour")
        
        # Assertions
        self.assertEqual(float(exchange.initiator_hourly_rate), 25.00)
        self.assertEqual(float(exchange.responder_hourly_rate), 50.00)
        self.assertEqual(float(exchange.initiator_hours_required), expected_hours_writer)
        self.assertEqual(float(exchange.responder_hours_required), expected_hours_designer)
        self.assertEqual(exchange.get_fairness_score(), 100.0)
        
        print("\n✅ TEST 2 PASSED: Reverse value exchange calculated correctly!")
        return True
    
    def test_3_equal_rate_exchange(self):
        """
        TEST 3: Same hourly rate (should be 1:1 hours)
        """
        print("\n" + "="*60)
        print("TEST 3: Equal Rate Exchange")
        print("Both at $40/hr should give 1:1 hours")
        print("="*60)
        
        # Create another developer with same rate
        dev2 = User.objects.create_user('dev_alex', 'alex@example.com', 'pass')
        dev2_offer = OfferedSkill.objects.create(
            user=dev2,
            skill=self.web_dev,
            hourly_rate_equivalent=40.00,  # Same as first developer
            is_active=True
        )
        
        exchange = SkillExchange.objects.create(
            initiator=self.developer,
            responder=dev2,
            skill_from_initiator=self.dev_offer,
            skill_from_responder=dev2_offer,
            terms="Code review exchange"
        )
        
        print(f"\n💰 Both at: ${exchange.initiator_hourly_rate}/hr")
        print(f"⏰ Hours: {exchange.initiator_hours_required}:{exchange.responder_hours_required}")
        
        # Assertions
        self.assertEqual(float(exchange.initiator_hourly_rate), 40.00)
        self.assertEqual(float(exchange.responder_hourly_rate), 40.00)
        self.assertEqual(float(exchange.calculated_ratio), 1.0)
        self.assertEqual(float(exchange.initiator_hours_required), 1.0)
        self.assertEqual(float(exchange.responder_hours_required), 1.0)
        self.assertEqual(exchange.get_fairness_score(), 100.0)
        
        print("\n✅ TEST 3 PASSED: Equal rates give 1:1 exchange!")
        return True
    
    def test_4_unfair_exchange_detection(self):
        """
        TEST 4: Manually set unfair hours to test fairness score
        """
        print("\n" + "="*60)
        print("TEST 4: Unfair Exchange Detection")
        print("="*60)
        
        # Create exchange but manually override hours to make it unfair
        exchange = SkillExchange.objects.create(
            initiator=self.designer,
            responder=self.developer,
            skill_from_initiator=self.design_offer,
            skill_from_responder=self.dev_offer,
        )
        
        # Manually set unfair hours (designer works 1 hour, developer works only 0.5 hours)
        # This should give low fairness score
        exchange.initiator_hours_required = 1.0
        exchange.responder_hours_required = 0.5  # Should be 1.25 for fairness
        exchange.save(skip_calculation=True)  # Save to recalculate fairness
        
        print(f"\n💰 Rates: ${exchange.initiator_hourly_rate}/hr ↔ ${exchange.responder_hourly_rate}/hr")
        print(f"⏰ Hours set to: {exchange.initiator_hours_required}:{exchange.responder_hours_required}")
        print(f"📊 Fairness Score: {exchange.get_fairness_score()}%")
        
        # Get detailed report
        report = exchange.get_detailed_fairness_report()
        print(f"🔍 Detailed Report:")
        print(f"  Initiator Value: ${report['initiator_value']}")
        print(f"  Responder Value: ${report['responder_value']}")
        print(f"  Value Difference: ${report['value_difference']}")
        
        # Should be low fairness score (around 40%)
        self.assertLess(report['fairness_score'], 50.0)
        self.assertFalse(report['is_balanced'])
        
        print("\n✅ TEST 4 PASSED: Unfair exchange properly detected!")
        return True
    
    def test_5_suggest_adjustment(self):
        """
        TEST 5: Check if adjustment suggestion works
        """
        print("\n" + "="*60)
        print("TEST 5: Adjustment Suggestions")
        print("="*60)
        
        exchange = SkillExchange.objects.create(
            initiator=self.designer,
            responder=self.writer,
            skill_from_initiator=self.design_offer,
            skill_from_responder=self.writing_offer,
        )
        
        # Make it slightly unfair
        exchange.initiator_hours_required = 1.0
        exchange.responder_hours_required = 1.5  # Should be 2.0 for perfect fairness
        exchange.save()
        
        print(f"\nCurrent setup:")
        print(f"  {exchange.initiator.username}: {exchange.initiator_hours_required} hour")
        print(f"  {exchange.responder.username}: {exchange.responder_hours_required} hours")
        print(f"  Current Fairness: {exchange.get_fairness_score()}%")
        
        suggestion = exchange.suggest_adjustment()
        
        if suggestion.get('adjustment_needed'):
            print(f"\n🔧 Adjustment Suggested:")
            print(f"  Perfect Ratio: {suggestion['perfect_ratio']}")
            print(f"  Suggested {exchange.initiator.username}: {suggestion['suggested_initiator_hours']} hours")
            print(f"  Suggested {exchange.responder.username}: {suggestion['suggested_responder_hours']} hours")
            
            # For Designer ($50) vs Writer ($25), perfect ratio is 2.0
            # So should suggest: Designer 1 hour, Writer 2 hours
            self.assertEqual(suggestion['suggested_responder_hours'], 2.0)
        else:
            print("\n⚠️ No adjustment needed (unexpected!)")
        
        self.assertTrue(suggestion.get('adjustment_needed', False))
        
        print("\n✅ TEST 5 PASSED: Adjustment suggestions work!")
        return True
    
    def test_6_validation_errors(self):
        """
        TEST 6: Ensure validation prevents invalid exchanges
        """
        print("\n" + "="*60)
        print("TEST 6: Validation Tests")
        print("="*60)
        
        # Test 6a: Self-exchange should raise error
        print("\nTesting self-exchange prevention...")
        exchange = SkillExchange(
            initiator=self.designer,
            responder=self.designer,  # Same user!
            skill_from_initiator=self.design_offer,
            skill_from_responder=self.design_offer,
        )
        
        with self.assertRaises(ValidationError):
            exchange.full_clean()  # This should raise ValidationError
        
        print("  ✓ Self-exchange properly prevented")
        
        print("\n✅ TEST 6 PASSED: Validation works correctly!")
        return True
    
    def test_7_edge_cases(self):
        """
        TEST 7: Edge cases and boundary conditions
        """
        print("\n" + "="*60)
        print("TEST 7: Edge Cases")
        print("="*60)
        
        # Test 7a: Very low rate
        print("\nTesting very low hourly rate ($1/hr)...")
        low_rate_user = User.objects.create_user('lowrate', 'low@example.com', 'pass')
        low_offer = OfferedSkill.objects.create(
            user=low_rate_user,
            skill=self.content_writing,
            hourly_rate_equivalent=1.00,  # Very low rate
        )

        
        
        exchange = SkillExchange.objects.create(
            initiator=low_rate_user,
            responder=self.designer,
            skill_from_initiator=low_offer,
            skill_from_responder=self.design_offer,
        )
        
        # Designer's $50/hr vs $1/hr = 50:1 ratio
        print(f"  $1/hr vs $50/hr = {exchange.calculated_ratio}:1 ratio")
        print(f"  {low_rate_user.username}: {exchange.initiator_hours_required} hours")
        print(f"  {self.designer.username}: {exchange.responder_hours_required} hours")
        
        self.assertEqual(float(exchange.calculated_ratio), 50.0)
        self.assertEqual(float(exchange.responder_hours_required), 1.0)
        self.assertEqual(float(exchange.initiator_hours_required), 50.0)
        
        print("  ✓ Very low rate handled correctly")
        
        print("\n✅ TEST 7 PASSED: Edge cases handled properly!")
        return True
    
    def test_8_complete_exchange_flow(self):
        """
        TEST 8: Simulate a complete exchange lifecycle
        """
        print("\n" + "="*60)
        print("TEST 8: Complete Exchange Lifecycle")
        print("="*60)
        
        # Create exchange
        exchange = SkillExchange.objects.create(
            initiator=self.designer,
            responder=self.developer,
            skill_from_initiator=self.design_offer,
            skill_from_responder=self.dev_offer,
            terms="Logo for website",
            status='pending'
        )
        
        print(f"\n1. Created: {exchange.get_exchange_summary()}")
        print(f"   Status: {exchange.status}")
        print(f"   Fairness: {exchange.get_fairness_score()}%")
        
        # Simulate negotiation
        exchange.status = 'negotiating'
        exchange.terms = "Logo + 2 revisions for responsive website"
        exchange.save()
        
        print(f"\n2. Negotiating: {exchange.status}")
        print(f"   Updated terms")
        
        # Simulate acceptance
        exchange.status = 'accepted'
        exchange.accepted_at = timezone.now()
        exchange.proposed_start_date = date.today()
        exchange.proposed_end_date = date.today() + timedelta(days=14)
        exchange.save()
        
        print(f"\n3. Accepted on: {exchange.accepted_at.date()}")
        print(f"   Timeline: {exchange.proposed_start_date} to {exchange.proposed_end_date}")
        
        # Simulate completion
        exchange.status = 'completed'
        exchange.completed_at = timezone.now()
        exchange.initiator_rating = 5
        exchange.responder_rating = 4
        exchange.initiator_feedback = "Great work!"
        exchange.save()
        
        print(f"\n4. Completed on: {exchange.completed_at}")
        print(f"   Ratings: {exchange.initiator_rating}/5 ↔ {exchange.responder_rating}/5")
        print(f"   Feedback: '{exchange.initiator_feedback}'")
        
        # Verify final state
        self.assertEqual(exchange.status, 'completed')
        self.assertIsNotNone(exchange.completed_at)
        self.assertEqual(exchange.initiator_rating, 5)
        self.assertEqual(exchange.responder_rating, 4)
        
        # Test helper methods
        print(f"\n5. Testing helper methods:")
        print(f"   Is {self.designer.username} a participant? {exchange.is_participant(self.designer)}")
        print(f"   Is {self.writer.username} a participant? {exchange.is_participant(self.writer)}")
        
        self.assertTrue(exchange.is_participant(self.designer))
        self.assertTrue(exchange.is_participant(self.developer))
        self.assertFalse(exchange.is_participant(self.writer))
        
        print(f"   Other party for {self.designer.username}: {exchange.get_other_party(self.designer).username}")
        
        self.assertEqual(exchange.get_other_party(self.designer), self.developer)
        self.assertEqual(exchange.get_other_party(self.developer), self.designer)
        
        print("\n✅ TEST 8 PASSED: Complete exchange lifecycle tested!")
        return True

def run_all_tests():
    """
    Function to run all tests manually if needed
    """
    print("Running all fairness tests...")
    test_case = FairnessCalculationTestCase()
    
    # Manually run each test
    tests = [
        test_case.test_1_basic_fair_exchange,
        test_case.test_2_reverse_value_exchange,
        test_case.test_3_equal_rate_exchange,
        test_case.test_4_unfair_exchange_detection,
        test_case.test_5_suggest_adjustment,
        test_case.test_6_validation_errors,
        test_case.test_7_edge_cases,
        test_case.test_8_complete_exchange_flow,
    ]
    
    for test in tests:
        try:
            test_case.setUp()  # Fresh data for each test
            test()
            print(f"✓ {test.__name__} passed\n")
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}\n")
    
    print("All tests completed!")

# This allows running the test file directly
if __name__ == "__main__":
    run_all_tests()