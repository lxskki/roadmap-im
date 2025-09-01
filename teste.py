import os
from dotenv import load_dotenv
from msrest.authentication import BasicAuthentication
from azure.devops.connection import Connection

load_dotenv()

ado_pat = os.getenv('ADO_PERSONAL_ACCESS_TOKEN')
ado_org_url = os.getenv('ADO_ORGANIZATION_URL')
ado_project_name = os.getenv('ADO_PROJECT_NAME')

try:
    credentials = BasicAuthentication('', ado_pat)
    connection = Connection(base_url=ado_org_url, creds=credentials)
    core_client = connection.clients.get_core_client()

    print(f"Tentando buscar o projeto: '{ado_project_name}'")
    project = core_client.get_project(ado_project_name)
    
    print("\nSUCESSO! Conexão com a organização e projeto está CORRETA.")
    print(f"ID do Projeto: {project.id}")
    print(f"Nome do Projeto: {project.name}")

except Exception as e:
    print("\nERRO! Não foi possível buscar o projeto.")
    print(f"Erro original: {e}")