import dash
from dash import html, dcc, Input, Output, State, MATCH, ctx
from dash.dependencies import ClientsideFunction
import pandas as pd
import os
from dotenv import load_dotenv
import re
from msrest.authentication import BasicAuthentication
from azure.devops.connection import Connection
from azure.devops.v7_1.work_item_tracking.models import TeamContext, Wiql

load_dotenv()

# ===============================
# CARREGAR E PREPARAR DADOS (DO AZURE DEVOPS)
# ===============================
try:
    ado_pat = os.getenv('ADO_PERSONAL_ACCESS_TOKEN')
    ado_org_url = os.getenv('ADO_ORGANIZATION_URL')
    ado_project_name = os.getenv('ADO_PROJECT_NAME')

    if not all([ado_pat, ado_org_url, ado_project_name]):
        raise ValueError("Uma ou mais variáveis de ambiente não foram encontradas.")

    credentials = BasicAuthentication('', ado_pat)
    connection = Connection(base_url=ado_org_url, creds=credentials)
    wit_client = connection.clients.get_work_item_tracking_client()
    print("Conectado ao Azure DevOps com sucesso!")

    team_context = TeamContext(project=ado_project_name)
    
    query_text = """
    SELECT
        [System.Id],
        [System.WorkItemType],
        [System.Title],
        [System.AssignedTo],
        [System.State],
        [System.AreaPath],
        [System.CreatedDate],
        [Microsoft.VSTS.Scheduling.StartDate],
        [Microsoft.VSTS.Scheduling.TargetDate],
        [System.Parent],
        [Microsoft.VSTS.Scheduling.Effort],
        [Microsoft.VSTS.Common.BusinessValue],
        [System.Tags],
        [Custom.data_incl],
        [Microsoft.VSTS.Common.ClosedDate]
    FROM workitems
    WHERE
        [System.TeamProject] = @project
        AND (
            [System.ChangedDate] > @today - 365
            AND (
                [System.WorkItemType] = 'Feature'
                OR [System.WorkItemType] = 'Projeto'
                OR [System.WorkItemType] = 'Epic'
                OR [System.WorkItemType] = 'User Story'
            )
            AND [System.State] <> ''
        )
    """
    
    wiql_object = Wiql(query=query_text)
    print("Executando query...")
    wiql_results = wit_client.query_by_wiql(wiql=wiql_object, team_context=team_context)
    print(f"Query retornou {len(wiql_results.work_items)} IDs.")

    if wiql_results.work_items:
        work_item_ids = [item.id for item in wiql_results.work_items]
        
        work_items_details = []
        chunk_size = 100
        
        for i in range(0, len(work_item_ids), chunk_size):
            chunk = work_item_ids[i:i + chunk_size]
            print(f"Buscando detalhes para o lote de IDs {i+1} a {i+len(chunk)}...")
            batch_details = wit_client.get_work_items(ids=chunk, expand="All")
            work_items_details.extend(batch_details)
        
        print(f"Detalhes de {len(work_items_details)} work items carregados com sucesso.")

        data_for_df = []
        for item in work_items_details:
            fields = item.fields
            data_for_df.append({
                'ID': item.id,
                'Work Item Type': fields.get('System.WorkItemType'),
                'Title': fields.get('System.Title'),
                'State': fields.get('System.State'),
                'Assigned To': fields.get('System.AssignedTo', {}).get('displayName', 'Não atribuído'),
                'Parent': fields.get('System.Parent'),
                'Start Date': fields.get('Microsoft.VSTS.Scheduling.StartDate'),
                'Target Date': fields.get('Microsoft.VSTS.Scheduling.TargetDate'),
                'Effort': fields.get('Microsoft.VSTS.Scheduling.Effort'),
                'Business Value': fields.get('Microsoft.VSTS.Common.BusinessValue'),
                'data_incl': fields.get('Custom.data_incl'),
            })
        
        df = pd.DataFrame(data_for_df)
        print("DataFrame criado com sucesso!")

    else:
        print("A query não retornou nenhum work item.")
        df = pd.DataFrame()

    numeric_cols = ['ID', 'Parent', 'Effort', 'Business Value']
    for col in numeric_cols:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        else: df[col] = pd.NA
    date_cols = ['Start Date', 'Target Date', 'data_incl']
    for col in date_cols:
        if col in df.columns: df[col] = pd.to_datetime(df[col], errors='coerce').dt.tz_localize(None)
        else: df[col] = pd.NaT
    df['Assigned To'] = df['Assigned To'].fillna('Não atribuído')
    df['State'] = df['State'].fillna('Não definido')
    if 'Assigned To' in df.columns and df['Assigned To'].dtype == 'object':
            df['Assigned To'] = df['Assigned To'].str.split('<').str[0].str.strip()
    dados_carregados = True

except Exception as e:
    print(f"!!!!!! ERRO AO CARREGAR DADOS DO AZURE DEVOPS !!!!!!")
    print(f"Erro original: {e}")
    df = pd.DataFrame()
    dados_carregados = False

# ===============================
# MAPEAMENTO DE ÁREAS E PESSOAS
# ===============================
AREAS = {
    'im': {'nome': 'Inteligência de Mercado', 'responsavel': 'Juliana Trevisan Rezende', 'image_file': 'Mercado.png'},
    'ecommerce': {'nome': 'E-commerce', 'responsavel': 'Beatriz Ridolfi Teixeira', 'image_file': 'Ecommerce.png'},
    'geo': {'nome': 'Inteligência Geográfica', 'responsavel': 'Sergio Ferreira da Silva', 'image_file': 'Geografico.png'},
    'negocios': {'nome': 'Inteligência de Negócios', 'responsavel': 'Adriano Santos Rodrigues', 'image_file': 'Negocios.png'},
    'estrategia': {'nome': 'Estratégia e Inteligência', 'responsavel': 'Wilgner Felix Pereira de Lima', 'image_file': 'Estrategia.png'},
    'consumo': {'nome': 'Inteligência de Consumo', 'responsavel': 'Fabiana Gomes Macedo Rossetti', 'image_file': 'Consumo.png'},
    'produto': {'nome': 'Gestão de Produto', 'responsavel': 'Henrique Aguiar Fraga', 'image_file': 'Produto.png'},
    'comunicacao': {'nome': 'Marca e Comunicação', 'responsavel': 'Julio Cesar Arantes Pollaria', 'image_file': 'Marca.png'}
}

PEOPLE_WITH_PHOTOS = [
    'Juliana Trevisan Rezende',#
    'Beatriz Ridolfi Teixeira',#
    'Sergio Ferreira da Silva', #
    'Adriano Santos Rodrigues', #
    'Wilgner Felix Pereira de Lima',#
    'Fabiana Gomes Macedo Rossetti', #
    'Henrique Aguiar Fraga', #
    'Julio Cesar Arantes Pollaria',# 
    'Isabela Santos do Nascimento', #
    'Lucas Oliveira da Silva',#
    'Grasiele Cristiane de Araujo Goncalves',# 
    'Kevin Axel Beltrame', #
    'Mariana Araujo de Oliveira Dias',# 
    'Yasmim Alves de Lima e Silva',#
    'Ana Luiza Sbruzzi Portela Figueiredo',# 
    'Arthur Davi Kikumiti Barros', #
    'Pedro Hack Schroder Silva', #
    'Giovanna Mendonca Valentim', #
    'Alini Ferreira Calvi',#
    'Ana Carolina de Morais Gamarra', #
    'Ana Carolina Leao Dos Santos', #
    'Carlos Eduardo Real Lopes', #
    'Emylle Katllen Cordeiro do Nascimento', #
    'Isadora Rossi', #
    'Izabelle Paulina Rocha Soares Moura', #
    'Jacqueline Dos Santos Rosario', #
    'Juliana Rodrigues Ferraz',#
    'Laura Zamaioli Taiacol', #
    'Matheus Platini de Araujo Barros', #
    'Mayara Soldado', #
    'Miguel Ishiara da Silva',#
    'Paulo Guilherme Junior', #
    'Sarah Maria Lima da Silva',#
    'Luiz Henrique Costa Perez',#
    'Thais Bitencourt Moreira de Oliveira'#
]

# ===============================
# FUNÇÕES AUXILIARES
# ===============================
def calcular_progresso_geral():
    if not dados_carregados or df.empty: return 0
    todas_atividades = df[df['Work Item Type'] == 'User Story']
    if len(todas_atividades) == 0: return 0
    atividades_concluidas = todas_atividades[todas_atividades['State'].str.lower().isin(['done', 'closed'])]
    return round((len(atividades_concluidas) / len(todas_atividades)) * 100, 1)

def criar_barra_progresso_geral():
    progresso_percent = calcular_progresso_geral()
    return html.Div(className='geral-progress-container', children=[
        html.Div(className='geral-progress-header', children=[
            html.H2('PROGRESSO GERAL DAS ATIVIDADES', className='geral-progress-title'),
            html.Span(f'{progresso_percent}%', className='geral-progress-text')
        ]),
        html.Div(className='geral-progress-bar', children=[
            html.Div(className='geral-progress-fill', style={'width': f'{progresso_percent}%'})
        ])
    ])

def formatar_nome_para_arquivo(nome):
    if not isinstance(nome, str): return ""
    nome_formatado = nome.lower()
    nome_formatado = re.sub(r'\s+', '-', nome_formatado)
    nome_formatado = re.sub(r'[^a-z0-9-]', '', nome_formatado)
    return nome_formatado

def get_person_assets(name):
    assets = {
        'Juliana Trevisan Rezende': {'strong': "#CA9716", 'light': '#FEF7E4', 'strong_shades': ["#CA9716", "#D39D15", "#E6B85C"], 'light_shades': ['#FEF7E4', '#FAF0D3', '#F8E8C2']},
        'Beatriz Ridolfi Teixeira': {'strong': '#8A2BE2', 'light': '#F3EFFF', 'strong_shades': ['#8A2BE2', '#A368E8', '#BE93EE'], 'light_shades': ['#F3EFFF', '#E9DFFF', '#DCD0EF']},
        'Sergio Ferreira da Silva': {'strong': '#005A9C', 'light': '#E6F0F9', 'strong_shades': ['#005A9C', '#337FBF', '#66A3D9'], 'light_shades': ['#E6F0F9', '#D9E7F5', '#CADDF0']},
        'Adriano Santos Rodrigues': {'strong': "#DD8923", 'light': '#FFF4E6', 'strong_shades': ['#DD8923', "#F09B34", '#FFBA66'], 'light_shades': ['#FFF4E6', '#FFEBD9', '#FFDECA']},
        'Wilgner Felix Pereira de Lima': {'strong': '#B22222', 'light': '#FFE5E5', 'strong_shades': ['#B22222', '#C65555', '#D98888'], 'light_shades': ['#FFE5E5', '#FFDADA', '#FFCECE']},
        'Fabiana Gomes Macedo Rossetti': {'strong': "#AA547F", 'light': '#FFF0F7', 'strong_shades': ['#AA547F', "#B9658F", "#C9709C"], 'light_shades': ['#FFF0F7', '#FFEBF2', '#FFE0EC']},
        'Henrique Aguiar Fraga': {'strong': '#808080', 'light': '#F2F2F2', 'strong_shades': ['#808080', '#999999', '#B3B3B3'], 'light_shades': ['#F2F2F2', '#E6E6E6', '#D9D9D9']},
        'Julio Cesar Arantes Pollaria': {'strong': '#639DA5', 'light': '#F0F6F7', 'strong_shades': ['#639DA5', '#82B1B7', '#A1C5C9'], 'light_shades': ['#F0F6F7', '#E6EFF0', '#DCE8E9']}
    }
    default_assets = {'strong': '#6c757d', 'light': '#f8f9fa', 'text': '#333741', 'strong_shades': ['#6c757d', '#868e96', '#adb5bd'], 'light_shades': ['#f8f9fa', '#e9ecef', '#dee2e6']}
    selected = assets.get(name, default_assets)
    selected['text_on_strong'] = '#FFFFFF'
    selected['photo_url'] = f'/assets/{formatar_nome_para_arquivo(name)}.png' if name in PEOPLE_WITH_PHOTOS else '/assets/default-avatar.png'
    return selected

def calcular_conclusao(item_id):
    if not dados_carregados or df.empty: return 0
    children = df[df['Parent'] == item_id]
    if len(children) == 0: return 0
    concluidas = children[children['State'].str.lower().isin(['done', 'closed'])]
    return round((len(concluidas) / len(children)) * 100, 1)

def criar_card_epic(epic_row):
    status_class = str(epic_row['State']).lower().replace(' ', '-')
    person_assets = get_person_assets(epic_row['Assigned To'])
    card_style = {'backgroundColor': person_assets['light'], 'borderLeft': f'5px solid {person_assets["strong"]}'}

    features_do_epic = df[(df['Parent'] == epic_row['ID']) & (df['Work Item Type'] == 'Feature')]
    total_features = len(features_do_epic)
    
    features_concluidas = features_do_epic[features_do_epic['State'].str.lower().isin(['done', 'closed'])]
    concluidas_count = len(features_concluidas)
    
    progresso_features_texto = f"{concluidas_count}/{total_features}"

    return html.Div(className='card epic-card-list epic-card-list-compact', style=card_style, children=[
        html.Div(className='card-body', children=[
            html.Div(className='card-header', children=[
                html.H4(epic_row['Title'], className='card-title-small'),
                html.Span(progresso_features_texto, className="status-badge") 
            ]),
            html.Div(className='epic-card-footer-aligned', children=[
                html.Div(f"{epic_row['Assigned To']}", className='epic-responsible'),
                dcc.Link('Ver Features', href=f'/epic/{epic_row["ID"]}', className='btn-epic-features', style={'backgroundColor': person_assets['strong']})
            ])
        ])
    ])

# ===============================
# COMPONENTES DE LAYOUT
# ===============================
def criar_header():
    return html.Div(className='header', children=[
        html.Div(className='header-content', children=[

            html.Div(id = 'logo-container', children = [
                dcc.Link(href='/', children=[
                html.Img(src='/assets/logo-escura.png', className='header-logo-base logo-padrao'),
                html.Img(src='/assets/logo-branca.png', className='header-logo-base logo-branca')
                ])
            ]),
          
            html.Div(className='header-title-center', children=[
                html.H1('MARKETING & INTELIGÊNCIA', className='header-title'),
                html.P('Roadmap Estratégico', className='header-subtitle')
            ]),

            html.Div(id='theme-switcher-container', children=[
                html.Button('🌙', id='theme-switcher-button', n_clicks=0, **{'data-dummy-output': ''})
            ])
        ])
    ])

def criar_breadcrumb(pathname):
    parts = [p for p in pathname.split('/') if p]
    breadcrumbs = [dcc.Link('Projetos', href='/')]
    url_path = ''
    for i, part in enumerate(parts):
        if part.isdigit():
            item_id = int(part)
            item_type = parts[i-1] if i > 0 else ''
            url_path += f'/{item_type}/{item_id}'
            try:
                title = df.loc[df['ID'] == item_id, 'Title'].iloc[0]
                breadcrumbs.extend([' › ', dcc.Link(title, href=url_path)])
            except IndexError:
                breadcrumbs.extend([' › ', "Item não encontrado"])
    return html.Div(className='breadcrumb', children=breadcrumbs)

def criar_card_projeto(row):
    epics_count = len(df[(df['Parent'] == row['ID']) & (df['Work Item Type'] == 'Epic')])
    person_assets = get_person_assets(row['Assigned To'])
    card_style = {'backgroundColor': person_assets['strong'], 'color': '#FFFFFF', 'border': 'none'}
    project_card = html.Div(className='card project-card-full', id={'type': 'project-card-clickable', 'index': row['ID']}, n_clicks=0, style=card_style, children=[
        html.Div(className='card-body', children=[
            html.H3(row['Title'], className='card-title'),
            html.P(row['Assigned To'], className='card-responsible')
        ]),
        html.Div(className='card-footer-alt', children=[
            html.Span(f"{epics_count} {'Epic' if epics_count == 1 else 'Epics'}", className='metric-badge'),
        ])
    ])
    return html.Div([project_card, html.Div(id={'type': 'epics-container', 'index': row['ID']}, className='epics-wrapper')])

# ===============================
# PÁGINAS
# ===============================
def pagina_projetos():
    sorted_areas = sorted(AREAS.items(), key=lambda item: item[1]['nome'])
    area_cards = []
    for key, area_info in sorted_areas:
        responsavel = area_info['responsavel']
        projetos_da_area = df[(df['Assigned To'] == responsavel) & (df['Work Item Type'] == 'Projeto')]
        total_projetos = len(projetos_da_area)
        person_assets = get_person_assets(responsavel)
        card = html.Div([
            html.Div(className='area-card', id={'type': 'area-card-clickable', 'index': key}, n_clicks=0, style={'borderLeft': f'8px solid {person_assets["strong"]}'}, children=[
                html.Img(src=f"/assets/areas/{area_info['image_file']}", className='area-image'),
                html.Div(className='area-content', children=[
                    html.H2(area_info['nome'], className='area-card-title'),
                    html.Span(f"{total_projetos} {'Projeto' if total_projetos == 1 else 'Projetos'}", className='area-card-badge')
                ])
            ]),
            html.Div(id={'type': 'projects-container', 'index': key}, className='projects-container-expandable')
        ])
        area_cards.append(card)
    return html.Div(className='page-container', children=[
        criar_breadcrumb('/'),
        criar_barra_progresso_geral(),
        html.Div(className='areas-wrapper', children=area_cards)
    ])

def criar_lista_de_tarefas(feature_id, colors):
    tasks = df[df['Parent'] == feature_id]
    if tasks.empty:
        return html.P("Nenhuma atividade encontrada para esta feature.", className="no-tasks-message")
    task_items = []
    light_shades = colors.get('light_shades', ['#e9ecef', '#dee2e6'])
    for i, (_, task) in enumerate(tasks.iterrows()):
        person_assets = get_person_assets(task['Assigned To'])
        task_style = {'backgroundColor': light_shades[i % len(light_shades)]}
        data_inclusao_str = task['data_incl'].strftime('%d/%m/%Y') if pd.notna(task['data_incl']) else 'N/A'
        item = html.Div(className='task-row', style=task_style, children=[
            html.Img(src=person_assets['photo_url'], className='task-photo'),
            html.Div(task['Title'], className='task-cell title'),
            html.Div(task['Assigned To'], className='task-cell responsible'),
            html.Div(data_inclusao_str, className='task-cell date'),
            html.Span(task['State'], className=f"status-badge status-{str(task['State']).lower().replace(' ', '-')}")
        ])
        task_items.append(item)
    return html.Div(className='tasks-list-colored', children=task_items)

def criar_header_features():
    return html.Div(className='features-header-row', children=[
        html.Div('Atividade', className='header-cell title'),
        html.Div('Responsável', className='header-cell responsible'),
        html.Div('Início', className='header-cell start-date'),
        html.Div('Entrega', className='header-cell target-date'),
        html.Div('Esforço', className='header-cell effort'),
        html.Div('Valor', className='header-cell business-value'),
        html.Div('Status', className='header-cell state'),
        html.Div('Progresso', className='header-cell progress'),
        html.Div('', className='header-cell expand-icon-container')
    ])

def criar_feature_row_expandable(feature, colors, index):
    progresso = calcular_conclusao(feature["ID"])
    strong_shades = colors.get('strong_shades', ['#6c757d', '#868e96', '#adb5bd'])
    row_style = {'backgroundColor': strong_shades[index % len(strong_shades)], 'color': colors['text_on_strong']}
    start_date_str = feature['Start Date'].strftime('%d/%m/%Y') if pd.notna(feature['Start Date']) else 'N/A'
    target_date_str = feature['Target Date'].strftime('%d/%m/%Y') if pd.notna(feature['Target Date']) else 'N/A'
    effort_str = int(feature['Effort']) if pd.notna(feature['Effort']) else 'N/A'
    value_str = int(feature['Business Value']) if pd.notna(feature['Business Value']) else 'N/A'
    return html.Div(className='feature-container', children=[
        html.Div(id={'type': 'feature-toggle', 'index': feature['ID']}, className='feature-row-expandable', style=row_style, n_clicks=0, children=[
            html.Div(feature['Title'], className='feature-cell title'),
            html.Div(feature['Assigned To'], className='feature-cell responsible'),
            html.Div(start_date_str, className='feature-cell start-date'),
            html.Div(target_date_str, className='feature-cell target-date'),
            html.Div(effort_str, className='feature-cell effort'),
            html.Div(value_str, className='feature-cell business-value'),
            html.Div(feature['State'], className='feature-cell state'),
            html.Div(className='feature-cell progress', children=[
                html.Span(f"{progresso}%"),
                html.Div(className='progress-bar-inline', children=[html.Div(className='progress-fill-inline', style={'width': f'{progresso}%'})])
            ]),
            html.Div(className='feature-cell expand-icon-container', children=[html.Span('▼', id={'type': 'expand-icon', 'index': feature['ID']})])
        ]),
        html.Div(id={'type': 'tasks-container', 'index': feature['ID']}, className='tasks-wrapper-expandable')
    ])

def pagina_features(epic_id):
    try:
        epic = df[df['ID'] == epic_id].iloc[0]
    except IndexError:
        return html.Div(className='page-container', children=[criar_breadcrumb(f'/epic/{epic_id}'), html.H2("Erro: Épico não encontrado")])
    features = df[(df['Parent'] == epic_id) & (df['Work Item Type'] == 'Feature')]
    project_id = epic.get('Parent')
    project_responsible = 'default'
    if pd.notna(project_id):
        try:
            project_responsible = df.loc[df['ID'] == project_id, 'Assigned To'].iloc[0]
        except IndexError: pass
    project_assets = get_person_assets(project_responsible)
    breadcrumb_path = f'/projeto/{project_id}/epic/{epic_id}' if pd.notna(project_id) else f'/epic/{epic_id}'
    if features.empty:
        feature_content = html.P("Nenhuma feature encontrada para este épico.", className='no-projects-message')
    else:
        features['Progresso'] = features['ID'].apply(calcular_conclusao)
        features = features.sort_values(by=['Business Value', 'Target Date', 'Progresso'], ascending=[False, True, True], na_position='last')
        feature_content = html.Div([
            criar_header_features(),
            html.Div([criar_feature_row_expandable(f, project_assets, i) for i, (_, f) in enumerate(features.iterrows())])
        ])
    return html.Div(className='page-container', children=[
        html.Div(className='breadcrumb-header', children=[
            criar_breadcrumb(breadcrumb_path),
            dcc.Link('‹ Voltar', href='/', className='btn-voltar-dinamico', style={'backgroundColor': project_assets['strong']})
        ]),
        feature_content
    ])

# ===============================
# CONFIGURAÇÃO DO APP
# ===============================
app = dash.Dash(__name__, suppress_callback_exceptions=True, assets_folder='assets')
server = app.server
app.title = "Roadmap Estratégico"

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    criar_header(),
    html.Div(id='page-content')
])

# ===============================
# CALLBACKS
# ===============================
@app.callback(Output('page-content', 'children'), [Input('url', 'pathname')])
def display_page(pathname):
    if not dados_carregados: return html.Div("Erro ao carregar dados.", className='error-message')
    if pathname == '/' or pathname is None: return pagina_projetos()
    elif pathname.startswith('/epic/'):
        try:
            epic_id = int(pathname.split('/')[2])
            return pagina_features(epic_id)
        except (ValueError, IndexError): return html.Div("ID de épico inválido.", className='error-message')
    else: return html.Div("Página não encontrada.", className='error-message')

@app.callback(Output({'type': 'projects-container', 'index': MATCH}, 'children'), Input({'type': 'area-card-clickable', 'index': MATCH}, 'n_clicks'), State({'type': 'projects-container', 'index': MATCH}, 'children'), prevent_initial_call=True)
def toggle_projects_area(n_clicks, current_children):
    if current_children: return []
    area_key = ctx.triggered_id['index']
    responsavel = AREAS[area_key]['responsavel']
    projetos_da_area = df[(df['Assigned To'] == responsavel) & (df['Work Item Type'] == 'Projeto')].sort_values(by='Title', ascending=True)
    if projetos_da_area.empty: return html.P("Nenhum projeto encontrado.", className='no-projects-message')
    return [criar_card_projeto(row) for _, row in projetos_da_area.iterrows()]

@app.callback(Output({'type': 'epics-container', 'index': MATCH}, 'children'), Input({'type': 'project-card-clickable', 'index': MATCH}, 'n_clicks'), State({'type': 'epics-container', 'index': MATCH}, 'children'), prevent_initial_call=True)
def toggle_epics_area(n_clicks, current_children):
    if not n_clicks: return dash.no_update
    if current_children: return []
    project_id = ctx.triggered_id['index']
    epics_do_projeto = df[(df['Parent'] == project_id) & (df['Work Item Type'] == 'Epic')]
    if epics_do_projeto.empty: return html.P("Este projeto não possui épicos.", className='no-projects-message')
    return [criar_card_epic(row) for _, row in epics_do_projeto.iterrows()]

@app.callback([Output({'type': 'tasks-container', 'index': MATCH}, 'children'), Output({'type': 'expand-icon', 'index': MATCH}, 'children')], [Input({'type': 'feature-toggle', 'index': MATCH}, 'n_clicks')], [State({'type': 'tasks-container', 'index': MATCH}, 'children')], prevent_initial_call=True)
def toggle_tasks_display(n_clicks, current_children):
    if not n_clicks: return dash.no_update, dash.no_update
    feature_id = ctx.triggered_id['index']
    if current_children: return [], '▼'
    else:
        try:
            feature = df.loc[df['ID'] == feature_id].iloc[0]
            epic = df.loc[df['ID'] == feature['Parent']].iloc[0]
            project = df.loc[df['ID'] == epic['Parent']].iloc[0]
            project_assets = get_person_assets(project['Assigned To'])
        except Exception:
            project_assets = get_person_assets('default')
        return criar_lista_de_tarefas(feature_id, project_assets), '▲'

app.clientside_callback(
    ClientsideFunction(namespace='clientside', function_name='toggleTheme'),
    Output('theme-switcher-button', 'data-dummy-output'),
    [Input('theme-switcher-button', 'n_clicks')],
    prevent_initial_call=True
)

if __name__ == '__main__':
    app.run(debug=True)