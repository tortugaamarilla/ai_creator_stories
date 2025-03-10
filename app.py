import streamlit as st
import openai
import pandas as pd
import uuid
from datetime import datetime

# Настройка заголовка и описания приложения
st.title("Генератор историй с помощью ChatGPT")
st.markdown("Создавайте и редактируйте истории с помощью ChatGPT на основе ваших заданий")

# Получение API ключей
try:
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    # Проверка наличия API ключа Anthropic
    has_anthropic_key = "ANTROPIC_API_KEY" in st.secrets and st.secrets["ANTROPIC_API_KEY"]
except:
    st.error("API ключ OpenAI не найден. Пожалуйста, укажите его в .streamlit/secrets.toml или в секретах streamlit.io")
    st.stop()

# Информация о ценах моделей
model_prices = {
    "gpt-4o": {"input": "$10.00 за 1M токенов", "output": "$30.00 за 1M токенов"},
    "gpt-4o-mini": {"input": "$0.15 за 1M токенов", "output": "$0.60 за 1M токенов"},
    "gpt-4.5-preview": {"input": "$5.00 за 1M токенов", "output": "$15.00 за 1M токенов"},
    "o1": {"input": "$15.00 за 1M токенов", "output": "$75.00 за 1M токенов"}
}

# Инициализация истории генераций
if 'story_history' not in st.session_state:
    st.session_state.story_history = []

# Инициализация выбранных историй
if 'selected_stories' not in st.session_state:
    st.session_state.selected_stories = []

# Функция для генерации истории
def generate_story(user_prompt, system_prompt, model, temperature):
    try:
        if model == "o1":
            # Проверка наличия ключа Anthropic
            if not has_anthropic_key:
                st.error("API ключ Anthropic не найден. Пожалуйста, укажите его в .streamlit/secrets.toml или в секретах streamlit.io")
                return None
                
            # Для модели Claude (o1) от Anthropic
            from anthropic import Anthropic
            client = Anthropic(api_key=st.secrets["ANTROPIC_API_KEY"])
            response = client.messages.create(
                model="claude-3-opus-20240229",  # o1 соответствует Claude-3-Opus
                max_tokens=4000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            content = response.content[0].text
        else:
            # Для моделей OpenAI
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature
            )
            content = response.choices[0].message.content
        
        story_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        story_data = {
            "id": story_id,
            "timestamp": timestamp,
            "user_prompt": user_prompt,
            "system_prompt": system_prompt,
            "model": model,
            "temperature": temperature if model != "o1" else None,
            "content": content
        }
        
        st.session_state.story_history.append(story_data)
        return story_data
    except Exception as e:
        st.error(f"Ошибка при генерации истории: {str(e)}")
        return None

# Функция для генерации новой версии истории на основе правок
def generate_revision(user_prompt, system_prompt, model, temperature, revision_prompt, selected_stories):
    try:
        # Подготовка сообщений для контекста
        context_messages = []
        for story in selected_stories:
            context_messages.append({"role": "user", "content": story["user_prompt"]})
            context_messages.append({"role": "assistant", "content": story["content"]})
            
        revision_message = f"Исправь историю согласно следующим требованиям: {revision_prompt}"
        
        if model == "o1":
            # Проверка наличия ключа Anthropic
            if not has_anthropic_key:
                st.error("API ключ Anthropic не найден. Пожалуйста, укажите его в .streamlit/secrets.toml или в секретах streamlit.io")
                return None
                
            # Для модели Claude (o1) от Anthropic
            from anthropic import Anthropic
            client = Anthropic(api_key=st.secrets["ANTROPIC_API_KEY"])
            
            # Преобразование сообщений в формат для Anthropic
            anthropic_messages = []
            for i in range(0, len(context_messages), 2):
                if i+1 < len(context_messages):
                    anthropic_messages.append({"role": "user", "content": context_messages[i]["content"]})
                    anthropic_messages.append({"role": "assistant", "content": context_messages[i+1]["content"]})
            
            # Добавление запроса на правку
            anthropic_messages.append({"role": "user", "content": revision_message})
            
            response = client.messages.create(
                model="claude-3-opus-20240229",  # o1 соответствует Claude-3-Opus
                max_tokens=4000,
                system=system_prompt,
                messages=anthropic_messages
            )
            content = response.content[0].text
        else:
            # Для моделей OpenAI
            client = openai.OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            
            all_messages = [{"role": "system", "content": system_prompt}]
            all_messages.extend(context_messages)
            all_messages.append({"role": "user", "content": revision_message})
            
            response = client.chat.completions.create(
                model=model,
                messages=all_messages,
                temperature=temperature
            )
            content = response.choices[0].message.content
        
        story_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        story_data = {
            "id": story_id,
            "timestamp": timestamp,
            "user_prompt": f"Правка: {revision_prompt}",
            "system_prompt": system_prompt,
            "model": model,
            "temperature": temperature if model != "o1" else None,
            "content": content,
            "based_on": [s["id"] for s in selected_stories]
        }
        
        st.session_state.story_history.append(story_data)
        return story_data
    except Exception as e:
        st.error(f"Ошибка при генерации правки: {str(e)}")
        return None

# Боковая панель для настроек
st.sidebar.header("Настройки")

# Выбор модели
model = st.sidebar.selectbox(
    "Выберите модель:",
    ["gpt-4o", "gpt-4o-mini", "gpt-4.5-preview", "o1"]
)

# Отображение информации о ценах
st.sidebar.subheader("Цены за использование модели:")
st.sidebar.markdown(f"**Входные данные**: {model_prices[model]['input']}")
st.sidebar.markdown(f"**Выходные данные**: {model_prices[model]['output']}")

# Настройка температуры для не-Anthropic моделей
if model != "o1":
    temperature = st.sidebar.slider("Температура:", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
else:
    st.sidebar.info("Модель o1 не поддерживает настройку температуры.")
    temperature = 0.7  # значение по умолчанию, не будет использоваться

# Основной интерфейс
tabs = st.tabs(["Создание истории", "История генераций", "Правки"])

with tabs[0]:
    st.header("Создание новой истории")
    
    system_prompt = st.text_area(
        "Системный промпт:",
        "Ты - креативный писатель, который создает интересные и увлекательные истории.",
        height=100
    )
    
    user_prompt = st.text_area(
        "Задание для истории:",
        "Напиши короткую историю о космическом путешествии на далекую планету.",
        height=150
    )
    
    if st.button("Сгенерировать историю"):
        with st.spinner("Генерация истории..."):
            story_data = generate_story(user_prompt, system_prompt, model, temperature)
            if story_data:
                st.success("История успешно сгенерирована!")
                st.markdown("### Результат:")
                st.markdown(story_data["content"])

with tabs[1]:
    st.header("История генераций")
    
    if not st.session_state.story_history:
        st.info("Истории пока нет. Сгенерируйте историю на вкладке 'Создание истории'.")
    else:
        for i, story in enumerate(reversed(st.session_state.story_history)):
            with st.expander(f"{i+1}. {story['timestamp']} - {story['user_prompt'][:50]}...", expanded=(i==0)):
                st.markdown(f"**Модель:** {story['model']}, **Температура:** {story['temperature'] if story['temperature'] is not None else 'Не применимо'}")
                st.markdown(f"**Системный промпт:** {story['system_prompt']}")
                st.markdown(f"**Задание:** {story['user_prompt']}")
                st.markdown("### Содержание:")
                st.markdown(story['content'])
                
                # Чекбокс для выбора истории для правок
                if st.checkbox("Выбрать для правки", key=f"select_{story['id']}"):
                    if story not in st.session_state.selected_stories:
                        st.session_state.selected_stories.append(story)
                else:
                    if story in st.session_state.selected_stories:
                        st.session_state.selected_stories.remove(story)

with tabs[2]:
    st.header("Правки историй")
    
    if not st.session_state.selected_stories:
        st.info("Выберите истории для правки на вкладке 'История генераций'.")
    else:
        st.subheader("Выбранные истории:")
        for i, story in enumerate(st.session_state.selected_stories):
            st.markdown(f"{i+1}. {story['timestamp']} - {story['user_prompt'][:50]}...")
        
        system_prompt_revision = st.text_area(
            "Системный промпт для правки:",
            "Ты - креативный редактор, который улучшает истории согласно требованиям.",
            height=100,
            key="system_prompt_revision"
        )
        
        revision_prompt = st.text_area(
            "Описание желаемых правок:",
            "Добавь больше деталей о технологиях космического корабля и опиши экипаж.",
            height=150,
            key="revision_prompt"
        )
        
        if st.button("Применить правки"):
            with st.spinner("Генерация новой версии..."):
                revised_story = generate_revision(
                    user_prompt="", 
                    system_prompt=system_prompt_revision, 
                    model=model, 
                    temperature=temperature, 
                    revision_prompt=revision_prompt, 
                    selected_stories=st.session_state.selected_stories
                )
                
                if revised_story:
                    st.success("Новая версия успешно сгенерирована!")
                    st.markdown("### Результат правки:")
                    st.markdown(revised_story["content"])
                    
                    # Сброс выбранных историй после правки
                    st.session_state.selected_stories = [] 