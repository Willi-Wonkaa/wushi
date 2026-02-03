import logging
import os
import sys
from datetime import timedelta
from pathlib import Path

import django
from asgiref.sync import sync_to_async

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wushu_analytics.settings')
django.setup()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from django.utils import timezone
from main.models import UserProfile, TelegramLoginToken

LOGIN_TOKEN_TTL_MINUTES = 5
LOGIN_BASE_URL = os.getenv('SITE_BASE_URL', 'http://localhost:8000')
LOGIN_PATH = '/auth/telegram/'

# Создаем синхронные функции для работы с Django ORM
@sync_to_async
def get_user_profile_by_telegram_id(telegram_id, verified_only=False):
    """Получить профиль пользователя по telegram_id"""
    try:
        if verified_only:
            return UserProfile.objects.get(telegram_id=telegram_id, is_telegram_verified=True)
        return UserProfile.objects.get(telegram_id=telegram_id)
    except UserProfile.DoesNotExist:
        return None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


@sync_to_async
def create_login_token(user, chat_id):
    """Создать одноразовую ссылку входа"""
    import secrets

    logger.info(f"Creating token for telegram_id={user.id}, username={user.username}, chat_id={chat_id}")

    TelegramLoginToken.objects.filter(telegram_id=user.id).delete()
    token_value = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES)

    token_obj = TelegramLoginToken.objects.create(
        telegram_id=user.id,
        telegram_username=user.username,
        telegram_first_name=user.first_name,
        telegram_last_name=user.last_name,
        telegram_chat_id=chat_id,
        token=token_value,
        expires_at=expires_at,
    )

    logger.info(f"Created token: {token_value[:8]}..., expires at: {expires_at}")
    return token_value


def build_login_link(token_value: str) -> str:
    base_url = LOGIN_BASE_URL.rstrip('/')
    return f"{base_url}{LOGIN_PATH}?token={token_value}"


async def send_login_link(update: Update) -> None:
    """Отправить пользователю ссылку для входа"""
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None

    logger.info(f"Creating login token for user {user.id}, username: {user.username}, chat_id: {chat_id}")

    try:
        token_value = await create_login_token(user, chat_id)
        login_link = build_login_link(token_value)
        
        logger.info(f"Created login link: {login_link}")

        await update.message.reply_html(
            f"🔐 Ваша ссылка для входа на сайт:\n"
            f"<a href=\"{login_link}\">Войти в Wushu Analytics</a>\n\n"
            f"⏰ Ссылка действует {LOGIN_TOKEN_TTL_MINUTES} минут."
        )
    except Exception as e:
        logger.error(f"Error creating login link: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании ссылки. Попробуйте еще раз."
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие при старте бота с отправкой ссылки входа"""
    user = update.effective_user

    profile = await get_user_profile_by_telegram_id(user.id)
    if profile and profile.is_telegram_verified:
        await update.message.reply_html(
            f"Добро пожаловать, {user.mention_html()}! "
            f"Ваш Telegram уже привязан к профилю {profile.user.username}.\n\n"
            f"Чтобы войти на сайт снова, используйте /login."
        )
        return

    await send_login_link(update)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать справку"""
    await update.message.reply_text(
        "📋 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/login - Получить ссылку для входа\n"
        "/help - Показать это сообщение\n"
        "/status - Проверить статус привязки\n"
        "/subscriptions - Показать мои подписки\n\n"
        "После привязки аккаунта вы будете получать уведомления об отслеживаемых соревнованиях, "
        "участниках и командах."
    )


async def login_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить новую ссылку для входа"""
    await send_login_link(update)


@sync_to_async
def get_subscriptions_count(profile):
    """Получить количество активных подписок"""
    return profile.subscriptions.filter(is_active=True).count()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверить статус привязки"""
    user = update.effective_user
    
    profile = await get_user_profile_by_telegram_id(user.id)
    if profile:
        if profile.is_telegram_verified:
            subscriptions_count = await get_subscriptions_count(profile)
            await update.message.reply_html(
                f"✅ Ваш аккаунт привязан к {profile.user.username}\n"
                f"📊 Активных подписок: {subscriptions_count}\n"
                f"👤 Telegram: @{profile.telegram_username}"
            )
        else:
            await update.message.reply_text(
                "❌ Ваш аккаунт найден, но не подтверждён.\n"
                "Используйте команду /login для получения ссылки."
            )
    else:
        await update.message.reply_text(
            "❌ Ваш аккаунт не найден в системе.\n"
            "Используйте /login для входа на сайт."
        )


@sync_to_async
def get_user_subscriptions(profile):
    """Получить подписки пользователя"""
    return list(profile.subscriptions.filter(is_active=True))

async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать подписки пользователя"""
    user = update.effective_user
    
    profile = await get_user_profile_by_telegram_id(user.id, verified_only=True)
    if profile:
        subscriptions = await get_user_subscriptions(profile)
        
        if not subscriptions:
            await update.message.reply_text(
                "📭 У вас нет активных подписок.\n"
                "Нажмите на колокольчики на сайте для отслеживания событий."
            )
            return
        
        message = "🔔 Ваши активные подписки:\n\n"
        
        for sub in subscriptions:
            message += f"• {sub.get_subscription_type_display()}: {sub.get_target_name()}\n"
        
        await update.message.reply_text(message)
    else:
        await update.message.reply_text(
            "❌ Сначала войдите на сайт через /login"
        )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на неизвестные сообщения"""
    await update.message.reply_text(
        "Я не понимаю эту команду. "
        "Используйте /help для списка доступных команд."
    )


def main() -> None:
    """Запуск бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    token = '8522111228:AAF5IShsFyp1Pjl7u6KJGO0y-6LmCgm53ck'
    if not token:
        raise RuntimeError('TELEGRAM_BOT_TOKEN is not set')

    application = Application.builder().token(token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("login", login_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("subscriptions", subscriptions_command))
    
    # Обработчик для остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Starting bot...")
    application.run_polling()
    

if __name__ == '__main__':
    main()
