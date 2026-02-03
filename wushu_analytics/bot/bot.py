import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import django
from pathlib import Path
from asgiref.sync import sync_to_async

# Django setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wushu_analytics.settings')
django.setup()

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from main.models import UserProfile

# Создаем синхронные функции для работы с Django ORM
@sync_to_async
def get_user_profile(telegram_id):
    """Получить профиль пользователя по telegram_id"""
    try:
        return UserProfile.objects.get(telegram_id=telegram_id)
    except UserProfile.DoesNotExist:
        return None

@sync_to_async
def get_user_profile_by_verification_code(code):
    """Получить профиль пользователя по коду верификации"""
    try:
        return UserProfile.objects.get(telegram_verification_code=code)
    except UserProfile.DoesNotExist:
        return None

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Приветствие при старте бота с генерацией секретного кода"""
    user = update.effective_user
    
    # Проверяем, есть ли пользователь в системе
    profile = await get_user_profile(user.id)
    if profile:
        if profile.is_telegram_verified:
            await update.message.reply_html(
                f"Добро пожаловать, {user.mention_html()}! "
                f"Ваш Telegram аккаунт уже привязан к профилю {profile.user.username}.\n\n"
                f"Используйте /subscriptions для просмотра подписок."
            )
        else:
            await update.message.reply_html(
                f"Привет, {user.mention_html()}! "
                f"Ваш профиль найден, но не подтверждён. "
                f"Используйте команду /verify <код> для подтверждения."
            )
    else:
        # Генерируем секретный код для нового пользователя
        import secrets
        secret_code = secrets.token_urlsafe(6)[:8].upper()  # 8 символов
        
        # Сохраняем временные данные в сессию или кэш
        context.user_data['secret_code'] = secret_code
        context.user_data['telegram_id'] = user.id
        context.user_data['telegram_username'] = user.username
        
        await update.message.reply_html(
            f"👋 Привет, {user.mention_html()}!\n\n"
            f"🔑 Ваш секретный код для регистрации на сайте:\n"
            f"<code>{secret_code}</code>\n\n"
            f"📝 Инструкция:\n"
            f"1. Перейдите на сайт и введите этот код\n"
            f"2. Ваш аккаунт будет создан автоматически\n"
            f"3. Telegram будет привязан для уведомлений\n\n"
            f"⏰ Код действителен 10 минут\n"
            f"💾 Сохраните этот код!"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать справку"""
    await update.message.reply_text(
        "📋 Доступные команды:\n\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать это сообщение\n"
        "/verify <код> - Подтвердить привязку аккаунта\n"
        "/status - Проверить статус привязки\n"
        "/subscriptions - Показать мои подписки\n\n"
        "После привязки аккаунта вы будете получать уведомления об отслеживаемых соревнованиях, "
        "участниках и командах."
    )


@sync_to_async
def update_profile_verification(profile, user, chat_id):
    """Обновление профиля верификации"""
    profile.telegram_id = user.id
    profile.telegram_username = user.username
    profile.telegram_chat_id = chat_id
    profile.is_telegram_verified = True
    profile.telegram_verification_code = None
    profile.save()

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Подтверждение привязки аккаунта"""
    if not context.args:
        await update.message.reply_text(
            "❌ Укажите код верификации.\n"
            "Используйте: /verify <ваш_код>"
        )
        return
    
    verification_code = context.args[0]
    user = update.effective_user
    
    try:
        # Ищем профиль по коду верификации
        profile = await get_user_profile_by_verification_code(verification_code)
        
        if profile:
            # Обновляем данные профиля
            await update_profile_verification(profile, user, update.effective_chat.id)
            
            await update.message.reply_html(
                f"✅ Отлично! Ваш Telegram аккаунт успешно привязан к профилю {profile.user.username}\n\n"
                f"Теперь вы будете получать уведомления об отслеживаемых событиях."
            )
        else:
            await update.message.reply_text(
                "❌ Неверный код верификации. "
                "Проверьте код в вашем профиле на сайте и попробуйте снова."
            )
        
    except Exception as e:
        logger.error(f"Error verifying user: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )


@sync_to_async
def get_subscriptions_count(profile):
    """Получить количество активных подписок"""
    return profile.subscriptions.filter(is_active=True).count()

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Проверить статус привязки"""
    user = update.effective_user
    
    profile = await get_user_profile(user.id)
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
                "Используйте команду /verify <код> для подтверждения."
            )
    else:
        await update.message.reply_text(
            "❌ Ваш аккаунт не найден в системе.\n"
            "Зарегистрируйтесь на сайте и привяжите Telegram."
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
            "❌ Сначала привяжите ваш аккаунт с помощью /verify <код>"
        )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ответ на неизвестные сообщения"""
    await update.message.reply_text(
        "Я не понимаю эту команду. "
        "Используйте /help для списка доступных команд."
    )


def main() -> None:
    """Запуск бота"""
    token = '8140856350:AAE1_7GCTr_I7nK7tWJh5zjO80E6zgPP7gU'

    application = Application.builder().token(token).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("verify", verify_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("subscriptions", subscriptions_command))
    
    # Обработчик для остальных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    logger.info("Starting bot...")
    application.run_polling()
    

if __name__ == '__main__':
    main()
