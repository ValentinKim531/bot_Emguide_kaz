# from openai import AsyncOpenAI
# from environs import Env
# import asyncio
#
# env = Env()
# env.read_env()
#
# OPENAI_API_KEY = env.str("OPENAI_API_KEY")
# ASSISTANT_ID = env.str("ASSISTANT_ID")
#
# client = AsyncOpenAI(api_key=env.str("OPENAI_API_KEY"))
#
#
# async def process_question(question):
#     thread = await client.beta.threads.create()
#
#     await client.beta.threads.messages.create(
#         thread_id=thread.id,
#         role="user",
#         content=question
#     )
#
#     run = await client.beta.threads.runs.create(
#         thread_id=thread.id,
#         assistant_id=ASSISTANT_ID
#     )
#
#     while run.status in ['queued', 'in_progress', 'cancelling']:
#         await asyncio.sleep(1)
#         run = await client.beta.threads.runs.retrieve(
#             thread_id=thread.id,
#             run_id=run.id
#         )
#
#     if run.status == 'completed':
#         messages = await client.beta.threads.messages.list(
#             thread_id=thread.id
#         )
#         assistant_messages = " ".join(msg.content[0].text.value for msg in messages.data if msg.role == 'assistant')
#         return assistant_messages
#     else:
#         return "Не удалось получить ответ от ассистента."
