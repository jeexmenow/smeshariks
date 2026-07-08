from django.test import Client, TestCase
from django.urls import reverse

from chat.models import CustomUser, Dialog, Message, Scenario, ScenarioStep
from chat.services.client_engine import get_or_create_active_dialog, handle_operator_turn


class TrainingFlowTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='trainee',
            email='trainee@example.com',
            password='pass12345',
        )
        self.scenario = Scenario.objects.create(
            title='Проверка доступа',
            client_name='Иван',
            situation='Клиент не может войти.',
            goal='Помочь восстановить доступ.',
            initial_message='Не могу войти в кабинет.',
            hints='Не просите пароль',
            is_active=True,
        )
        ScenarioStep.objects.create(
            scenario=self.scenario,
            step_number=1,
            client_message='Да, доступ к почте есть.',
            expected_operator_response='Уточнить email и не просить пароль.',
            keywords='email,пароль',
        )
        ScenarioStep.objects.create(
            scenario=self.scenario,
            step_number=2,
            client_message='Спасибо, попробую восстановить доступ.',
            expected_operator_response='Предложить восстановление доступа.',
            keywords='восстанов',
            is_final=True,
        )

    def test_get_or_create_active_dialog_starts_scenario(self):
        dialog = get_or_create_active_dialog(self.user)

        self.assertEqual(dialog.scenario, self.scenario)
        self.assertEqual(dialog.client_name, 'Иван')
        self.assertEqual(dialog.messages.count(), 1)
        self.assertEqual(dialog.messages.first().role, Message.ROLE_CLIENT)

    def test_operator_turn_creates_evaluation_and_client_reply(self):
        dialog = get_or_create_active_dialog(self.user)

        turn = handle_operator_turn(dialog, 'Здравствуйте, уточните email, пароль не присылайте.', self.user)

        self.assertTrue(turn.continue_dialog)
        self.assertEqual(turn.operator_message.role, Message.ROLE_OPERATOR)
        self.assertGreaterEqual(turn.operator_message.score, 70)
        self.assertEqual(turn.client_message.text, 'Да, доступ к почте есть.')
        self.assertEqual(dialog.evaluations.count(), 1)

    def test_send_message_endpoint_returns_training_payload(self):
        dialog = get_or_create_active_dialog(self.user)
        client = Client()
        client.login(username='trainee', password='pass12345')

        response = client.post(reverse('send_message'), {
            'dialog_id': dialog.id,
            'text': 'Здравствуйте, уточните email, пароль не присылайте.',
        })

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['status'], 'ok')
        self.assertTrue(payload['continue_dialog'])
        self.assertIn('dialogs', payload)
        self.assertEqual(Dialog.objects.get(id=dialog.id).current_step, 2)
