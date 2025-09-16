from setuptools import setup, find_packages

setup(
    name='mcp_multiagent',
    version='0.1.0',
    description='A multi-agent system framework based on MCP protocol, supporting multiple LLM agents with user-defined API keys and multi-protocol communication.',
    author='Your Name',
    packages=find_packages(),
    install_requires=[
        'mcp',
        'openai',
        'grpcio',
        'grpcio-tools',
        'websockets',
        'fastapi',
        'uvicorn',
        'pydantic',
        'httpx',
    ],
    python_requires='>=3.8',
) 