from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from Campaign.models import Campaign
from EvalData.models import ContrastiveAssessmentDocumentResult
from EvalData.models import ContrastiveAssessmentDocumentTask
from EvalData.models import Market
from EvalData.models import Metadata
from EvalData.models import ObjectID
from EvalData.models import TASK_DEFINITIONS
from EvalData.models import TaskAgenda
from EvalData.models import TextSegment
from EvalData.models import TextSegmentWithThreeTargetsWithContext


class TaskAgendaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create valid User and Campaign instances to test TaskAgenda with.
        """
        super(TaskAgendaTests, cls).setUpClass()

        cls.valid_user = User()
        cls.valid_user.username = 'dummy-user'
        cls.valid_user.save()

        cls.valid_campaign = Campaign()
        cls.valid_campaign.createdBy = cls.valid_user
        cls.valid_campaign.save()

    def test_cannot_complete_non_existing_task(self):
        agenda = TaskAgenda.objects.create(
            user=self.valid_user, campaign=self.valid_campaign
        )

        non_existing_task = 'does-not-exist'
        expected_message = 'Invalid task {0!r} not ObjectID ' 'instance'.format(
            non_existing_task
        )
        with self.assertRaisesMessage(ValueError, expected_message):
            agenda.complete_open_task(non_existing_task)

    def test_completed_task_moved_correctly(self):
        """
        Completing an open task moves it from _open_tasks to _completed_tasks.
        """
        agenda = TaskAgenda.objects.create(
            user=self.valid_user, campaign=self.valid_campaign
        )

        dummy_task = ObjectID.objects.create(
            typeName='DirectAssessmentTask', primaryID='123'
        )
        agenda._open_tasks.add(dummy_task)

        agenda.complete_open_task(dummy_task)
        self.assertFalse(dummy_task in agenda._open_tasks.all())
        self.assertTrue(dummy_task in agenda._completed_tasks.all())


class TaskAgendaResetTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='reset-user')
        cls.campaign = Campaign.objects.create(
            campaignName='contrastive-one', createdBy=cls.user
        )
        cls.other_campaign = Campaign.objects.create(
            campaignName='contrastive-two', createdBy=cls.user
        )
        market = Market.objects.create(
            sourceLanguageCode='eng',
            targetLanguageCode='deu',
            domainName='TEST',
            createdBy=cls.user,
        )
        metadata = Metadata.objects.create(
            market=market,
            corpusName='TEST',
            versionInfo='1.0',
            source='TEST',
            createdBy=cls.user,
        )
        item = TextSegmentWithThreeTargetsWithContext.objects.create(
            itemID=1,
            itemType='TGT',
            metadata=metadata,
            segmentID='1',
            segmentText='Source',
            target1ID='system-1',
            target1Text='Target',
            documentID='document-1',
            createdBy=cls.user,
        )
        cls.task = ContrastiveAssessmentDocumentTask.objects.create(
            campaign=cls.campaign,
            requiredAnnotations=1,
            batchNo=1,
            createdBy=cls.user,
        )
        cls.other_task = ContrastiveAssessmentDocumentTask.objects.create(
            campaign=cls.other_campaign,
            requiredAnnotations=1,
            batchNo=1,
            createdBy=cls.user,
        )
        cls.task_id = ObjectID.objects.create(
            typeName=cls.task.__class__.__name__, primaryID=cls.task.id
        )
        cls.other_task_id = ObjectID.objects.create(
            typeName=cls.other_task.__class__.__name__, primaryID=cls.other_task.id
        )
        cls.result = ContrastiveAssessmentDocumentResult.objects.create(
            score1=50,
            start_time=0,
            end_time=1,
            item=item,
            task=cls.task,
            createdBy=cls.user,
            modifiedBy=cls.user,
        )
        cls.other_result = ContrastiveAssessmentDocumentResult.objects.create(
            score1=50,
            start_time=0,
            end_time=1,
            item=item,
            task=cls.other_task,
            createdBy=cls.user,
            modifiedBy=cls.user,
        )
        cls.agenda = TaskAgenda.objects.create(
            user=cls.user, campaign=cls.campaign
        )
        cls.agenda._completed_tasks.add(cls.task_id)
        cls.other_agenda = TaskAgenda.objects.create(
            user=cls.user, campaign=cls.other_campaign
        )
        cls.other_agenda._completed_tasks.add(cls.other_task_id)

    def test_reset_contrastive_agenda_only_retires_its_results(self):
        reset, _, _ = self.agenda.reset_taskagenda()

        self.assertTrue(reset)
        shadow_user = User.objects.get(username='reset-user-01')
        self.result.refresh_from_db()
        self.other_result.refresh_from_db()
        self.assertEqual(self.result.createdBy, shadow_user)
        self.assertEqual(self.result.modifiedBy, shadow_user)
        self.assertTrue(self.result.retired)
        self.assertEqual(self.other_result.createdBy, self.user)
        self.assertEqual(self.other_result.modifiedBy, self.user)
        self.assertFalse(self.other_result.retired)
        self.assertIn(self.task_id, self.agenda._open_tasks.all())
        self.assertNotIn(self.task_id, self.agenda._completed_tasks.all())
        self.assertIn(self.other_task_id, self.other_agenda._completed_tasks.all())

    def test_all_registered_result_types_support_task_scoping(self):
        for _, task_class, result_class, *_ in TASK_DEFINITIONS:
            with self.subTest(task_class=task_class.__name__):
                task_field = result_class._meta.get_field('task')
                self.assertIs(task_field.related_model, task_class)


class MarketTests(TestCase):
    def test_cannot_exceed_max_length_for_source_language_code(self):
        pass

    def test_cannot_exceed_max_length_for_target_language_code(self):
        pass

    def test_cannot_exceed_max_length_for_domain_name(self):
        pass

    def test_cannot_recreate_existing_market(self):
        pass

    def test_cannot_modify_market_id(self):
        pass


class MetadataTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create valid Market instance to test Metadata with.
        """
        super(MetadataTests, cls).setUpClass()

        cls.valid_user = User()
        cls.valid_user.username = 'dummy-user'
        cls.valid_user.save()

        cls.valid_market = Market()
        cls.valid_market.sourceLanguageCode = "en-US"
        cls.valid_market.targetLanguageCode = "de-DE"
        cls.valid_market.domainName = "TEST"
        cls.valid_market.createdBy = cls.valid_user
        cls.valid_market.save()

        cls.createdBy = cls.valid_user

    def test_cannot_exceed_maxlength_for_corpus_name(self):
        pass

    def test_cannot_exceed_maxlength_for_version_info(self):
        pass

    def test_cannot_exceed_maxlength_for_source(self):
        pass

    def test_cannot_not_set_market(self):
        pass


class TextSegmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Create valid Market and Metadata instances to test TextSegment with.
        """
        super(TextSegmentTests, cls).setUpClass()

        cls.valid_user = User()
        cls.valid_user.username = 'dummy-user'
        cls.valid_user.save()

        cls.valid_market = Market()
        cls.valid_market.sourceLanguageCode = "en-US"
        cls.valid_market.targetLanguageCode = "de-DE"
        cls.valid_market.domainName = "TEST"
        cls.valid_market.createdBy = cls.valid_user
        cls.valid_market.save()

        cls.valid_metadata = Metadata()
        cls.valid_metadata.market = cls.valid_market
        cls.valid_metadata.corpusName = "TEST"
        cls.valid_metadata.versionInfo = "1.0"
        cls.valid_metadata.source = "MANUAL"
        cls.valid_metadata.createdBy = cls.valid_user
        cls.valid_metadata.save()

        cls.valid_textsegment = TextSegment()
        cls.valid_textsegment.itemID = 1
        cls.valid_textsegment.itemType = 'SRC'
        cls.valid_textsegment.segmentID = 'SomeID'
        cls.valid_textsegment.segmentText = 'This is a test sentence.'
        cls.valid_textsegment.metadata = TextSegmentTests.valid_metadata
        cls.valid_textsegment.createdBy = TextSegmentTests.valid_user
        cls.valid_textsegment.save()

    def test_valid_instance_has_createdby(self):
        """
        Test that valid instance has createdBy set.
        """
        self.assertTrue(hasattr(TextSegmentTests.valid_textsegment, 'createdBy'))

    def test_valid_instance_has_datecreated(self):
        """
        Test that valid instance has dateCreated set.
        """
        self.assertTrue(hasattr(TextSegmentTests.valid_textsegment, 'dateCreated'))

    def test_cannot_use_negative_integer_as_id(self):
        """
        sentenceID is a PositiveIntegerField and hence should
        never accept negative integer values.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemID = -1
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_use_zero_integer_as_id(self):
        """
        sentenceID is a PositiveIntegerField so 0 is technically
        a legal value. Our IDs are 1-based, so we want to reject
        any zero-based IDs.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemID = 0
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_use_non_integer_as_id(self):
        """
        sentenceID is a PositiveIntegerField and hence should
        never accept non integer typed data.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemID = '1'
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_use_non_string_as_text(self):
        """
        sentenceText is a CharField and hence should never accept
        non string typed data.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = 123
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_use_empty_string_as_text(self):
        """
        sentenceText is a CharField and hence should never accept
        an empty string as value.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = ''
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_use_too_long_string_as_text(self):
        """
        sentenceText is a CharField and hence should never accept
        a string longer than .models.MAX_SEGMENTTEXT_LENGTH as value.
        """
        from EvalData.models import MAX_SEGMENTTEXT_LENGTH

        _too_long_string = 'a' * (MAX_SEGMENTTEXT_LENGTH + 1)

        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = _too_long_string
        self.assertEqual(len(_too_long_string), MAX_SEGMENTTEXT_LENGTH + 1)
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_not_set_itemid(self):
        """
        itemID cannot be left blank.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemID = None
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_not_set_segmenttext(self):
        """
        segmentText cannot be left blank.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = None
        self.assertEqual(test_obj.is_valid(), False)

    def test_can_set_unicode_text(self):
        """
        sentenceText should accept Unicode text.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = 'This is ä test contäining ümläütß.'
        self.assertEqual(test_obj.is_valid(), True)

    def test_can_set_correct_length_unicode_text(self):
        """
        sentenceText should accept up to max_length Unicode characters.
        """
        from EvalData.models import MAX_SEGMENTTEXT_LENGTH

        _correct_length_string = '\u0394' * MAX_SEGMENTTEXT_LENGTH

        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentText = _correct_length_string
        self.assertEqual(test_obj.is_valid(), True)

    def test_cannot_not_set_metadata(self):
        """
        metadata cannot be left blank.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.metadata = None
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_not_set_itemtype(self):
        """
        itemType cannot be left blank.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemtype = None
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_not_set_segmentid(self):
        """
        segmentID cannot be left blank.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.segmentID = None
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_set_wrong_itemtype(self):
        """
        itemType cannot be set to unknown value.
        """
        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemType = 'FOO'
        self.assertEqual(test_obj.is_valid(), False)

    def test_cannot_set_too_long_itemtype(self):
        """
        itemType cannot be set to too long value.
        """
        from EvalData.models import MAX_SEGMENTID_LENGTH

        _too_long_bad_itemtype = 'F' * (MAX_SEGMENTID_LENGTH + 1)

        test_obj = TextSegmentTests.valid_textsegment
        test_obj.itemType = _too_long_bad_itemtype
        self.assertEqual(test_obj.is_valid(), False)

    def test_can_set_correct_itemtype(self):
        """
        itemType can be set to known values.
        """
        from EvalData.models import SET_ITEMTYPE_CHOICES

        test_obj = TextSegmentTests.valid_textsegment

        for itemtype in SET_ITEMTYPE_CHOICES:
            test_obj.itemType = itemtype[0]
            self.assertEqual(test_obj.is_valid(), True)
