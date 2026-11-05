"""
Script para popular o banco de dados do Estok com dados fictícios de demonstração.
Cria empresas (entidades), funcionários (usuários), catálogo de suprimentos,
pedidos de compra, solicitações de recursos em múltiplos estados e histórico de movimentações.

TODAS as senhas de usuários são configuradas como '123'.
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta
import random

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from werkzeug.security import generate_password_hash
from app.db import conectar


def semear_dados():
    print("[*] Iniciando geração de dados fictícios para demonstração...")
    senha_hash_123 = generate_password_hash("123")
    agora = datetime.now()

    with conectar() as conn, conn.cursor() as cur:
        # Desativa chaves estrangeiras temporariamente para limpeza/reestruturação ordenada
        cur.execute("SET FOREIGN_KEY_CHECKS = 0;")

        # Limpa dados operacionais anteriores para evitar duplicações
        cur.execute("TRUNCATE TABLE historico_solicitacao;")
        cur.execute("TRUNCATE TABLE item_solicitacao;")
        cur.execute("TRUNCATE TABLE solicitacao;")
        cur.execute("TRUNCATE TABLE item_pedido_compra;")
        cur.execute("TRUNCATE TABLE pedido_compra;")
        cur.execute("TRUNCATE TABLE movimentacao_estoque;")
        cur.execute("TRUNCATE TABLE suprimento;")
        cur.execute("TRUNCATE TABLE usuario_perfil;")
        cur.execute("TRUNCATE TABLE usuario;")
        cur.execute("TRUNCATE TABLE entidade;")

        cur.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # =========================================================================
        # 1. ENTIDADES / EMPRESAS
        # =========================================================================
        print("[+] Criando empresas (entidades)...")
        entidades = [
            (1, "Estok Matriz (Vitória)", "MATRIZ-VIX", 1),
            (2, "UVV - Campus Boa Vista", "UVV-BOAVISTA", 1),
            (3, "Logística & Distribuição Serra", "LOG-SERRA", 1),
            (4, "Hospital Santa Maria", "HOSP-SM", 1),
            (5, "Indústria & Manutenção Cariacica", "IND-CAR", 1),
        ]
        cur.executemany("""
            INSERT INTO entidade (id, nome, identificador, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, NOW(), NOW())
        """, entidades)

        # =========================================================================
        # 2. USUÁRIOS E PERFIS (Todos com senha = '123')
        # =========================================================================
        print("[+] Cadastrando usuários e atribuindo perfis (senha de todos = '123')...")
        # Perfis: 1: SUPER_ADMIN, 2: GERENTE, 3: GESTOR, 4: SOLICITANTE, 5: ADMIN
        usuarios_dados = [
            # Super-Admin global (todos os perfis)
            (1, None, 1, "admin", "Super Administrador", "admin@estok.com", [1, 5, 2, 3, 4]),

            # Usuário do Michel Salles (com múltiplos perfis para demonstrar troca de perfil)
            (2, 1, 5, "michel.salles", "Michel Salles", "michel.salles@estok.com", [5, 2, 3, 4]),

            # Usuários padrão de teste (Matriz)
            (3, 1, 5, "admin.entidade", "Administrador da Entidade", "admin.entidade@estok.com", [5]),
            (4, 1, 2, "gerente", "Gerente de Suprimentos", "gerente@estok.com", [2]),
            (5, 1, 3, "gestor", "Gestor de Almoxarifado", "gestor@estok.com", [3]),
            (6, 1, 4, "solicitante", "Solicitante Geral", "solicitante@estok.com", [4]),

            # Funcionários Estok Matriz
            (7, 1, 5, "carla.mendes", "Carla Mendes", "carla.mendes@estok.com", [5]),
            (8, 1, 2, "rodrigo.almeida", "Rodrigo Almeida", "rodrigo.almeida@estok.com", [2]),
            (9, 1, 3, "felipe.costa", "Felipe Costa", "felipe.costa@estok.com", [3]),
            (10, 1, 4, "patricia.souza", "Patrícia Souza", "patricia.souza@estok.com", [4]),
            (11, 1, 4, "lucas.ferreira", "Lucas Ferreira", "lucas.ferreira@estok.com", [4]),

            # Funcionários UVV Campus Boa Vista
            (12, 2, 5, "bruno.torres", "Bruno Torres", "bruno.torres@uvv.br", [5, 2]),
            (13, 2, 2, "marcos.professor", "Marcos Aurélio", "marcos.aurelio@uvv.br", [2]),
            (14, 2, 3, "mariana.ribeiro", "Mariana Ribeiro", "mariana.ribeiro@uvv.br", [3]),
            (15, 2, 4, "juliana.lima", "Juliana Lima", "juliana.lima@uvv.br", [4]),
            (16, 2, 4, "thiago.santos", "Thiago Santos", "thiago.santos@uvv.br", [4]),

            # Funcionários Logística Serra
            (17, 3, 5, "marcos.oliveira", "Marcos Oliveira", "marcos.oliveira@logserra.com", [5]),
            (18, 3, 2, "aline.castro", "Aline Castro", "aline.castro@logserra.com", [2]),
            (19, 3, 3, "andre.martins", "André Martins", "andre.martins@logserra.com", [3]),
            (20, 3, 4, "gabriel.duarte", "Gabriel Duarte", "gabriel.duarte@logserra.com", [4]),

            # Funcionários Hospital Santa Maria
            (21, 4, 5, "beatriz.nunes", "Beatriz Nunes", "beatriz.nunes@hospitalsm.com", [5]),
            (22, 4, 2, "fernando.dias", "Dr. Fernando Dias", "fernando.dias@hospitalsm.com", [2]),
            (23, 4, 3, "renata.barbosa", "Renata Barbosa", "renata.barbosa@hospitalsm.com", [3]),
            (24, 4, 4, "camila.vieira", "Enf. Camila Vieira", "camila.vieira@hospitalsm.com", [4]),
            (25, 4, 4, "diego.moreira", "Diego Moreira", "diego.moreira@hospitalsm.com", [4]),

            # Funcionários Indústria Cariacica
            (26, 5, 5, "eduardo.ramos", "Eduardo Ramos", "eduardo.ramos@indcariacica.com", [5]),
            (27, 5, 2, "vanessa.pires", "Eng. Vanessa Pires", "vanessa.pires@indcariacica.com", [2]),
            (28, 5, 3, "leandro.gomes", "Leandro Gomes", "leandro.gomes@indcariacica.com", [3]),
            (29, 5, 4, "marcelo.teixeira", "Marcelo Teixeira", "marcelo.teixeira@indcariacica.com", [4]),
        ]

        for uid, ent_id, p_id, login, nome, email, perfis in usuarios_dados:
            cur.execute("""
                INSERT INTO usuario (id, entidade_id, perfil_id, login, nome, email, senha_hash, status, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, NOW(), NOW())
            """, (uid, ent_id, p_id, login, nome, email, senha_hash_123))

            for pid in perfis:
                cur.execute("INSERT INTO usuario_perfil (usuario_id, perfil_id) VALUES (%s, %s)", (uid, pid))

        # =========================================================================
        # 3. CATÁLOGO DE SUPRIMENTOS (Por Entidade)
        # =========================================================================
        print("[+] Cadastrando catálogo de suprimentos com estoque e níveis de reposição...")
        # (id, entidade_id, nome, codigo_interno, unidade_medida, descricao, estoque_minimo, estoque_atual, status)
        suprimentos_dados = [
            # Entidade 1 - Estok Matriz (Geral / Escritório / TI)
            (1, 1, "Cabo de Rede UTP Cat6 100% Cobre", "INF-001", "cx", "Caixa com 305 metros cabo azul homologado Anatel", 5, 12, 1),
            (2, 1, "Conector RJ45 Cat6 Macho Blindado", "INF-002", "pct", "Pacote com 100 unidades banhado a ouro", 10, 28, 1),
            (3, 1, "Teclado USB Padrão ABNT2 Preto", "INF-003", "un", "Teclado membrana USB resistente a respingos", 15, 8, 1), # Abaixo do mínimo!
            (4, 1, "Mouse Óptico USB 1200 DPI Preto", "INF-004", "un", "Mouse ergonômico 3 botões com scroll", 15, 6, 1), # Abaixo do mínimo!
            (5, 1, "SSD NVMe 500GB M.2 PCIe 4.0", "INF-005", "un", "Armazenamento alta velocidade para desktops", 8, 14, 1),
            (6, 1, "Toner Compatível HP W1105A / 105A", "INF-006", "un", "Cartucho toner preto rendimento 1.000 páginas", 6, 3, 1), # Abaixo do mínimo!
            (7, 1, "Papel Sulfite A4 75g Caixa 10 Resmas", "ESC-001", "cx", "Caixa com 5.000 folhas brancas 75g/m²", 20, 45, 1),
            (8, 1, "Caneta Esferográfica Azul 1.0mm", "ESC-002", "cx", "Caixa com 50 canetas corpo transparente", 10, 25, 1),
            (9, 1, "Bloco Autoadesivo Amarelo 76x76mm", "ESC-003", "pct", "Bloco tipo Post-it com 100 folhas", 20, 18, 1), # Abaixo do mínimo!
            (10, 1, "Álcool 70% Líquido Galão 5L", "LIMP-001", "gl", "Galão de álcool etílico hidratado 70° INPM", 10, 22, 1),
            (11, 1, "Café em Pó Tradicional 500g", "COPA-001", "pct", "Pacote de café a vácuo torrado e moído", 15, 30, 1),
            (12, 1, "Papel Toalha Interfolhado 2 Dobras", "LIMP-002", "fardo", "Fardo com 1.000 folhas celulose virgem", 12, 10, 1), # Abaixo do mínimo!

            # Entidade 2 - UVV Campus Boa Vista (Acadêmico / Laboratórios / Informática)
            (13, 2, "Papel Sulfite A4 75g Caixa 10 Resmas", "UVV-ESC-01", "cx", "Caixa com 10 resmas para impressões da coordenação", 25, 60, 1),
            (14, 2, "Pincel Atômico para Quadro Branco Azul", "UVV-ESC-02", "cx", "Caixa com 12 marcadores recarregáveis", 15, 40, 1),
            (15, 2, "Apagador para Quadro Branco com Feltro", "UVV-ESC-03", "un", "Apagador magnético com porta-marcador", 10, 25, 1),
            (16, 2, "Cabo HDMI 2.0 Blindado 3 Metros", "UVV-INF-01", "un", "Cabo para ligação de projetores e TVs das salas", 12, 5, 1), # Abaixo do mínimo!
            (17, 2, "Mouse Óptico USB 1200 DPI", "UVV-INF-02", "un", "Para reposição nos laboratórios de informática", 20, 15, 1),
            (18, 2, "Pilha Alcalina AAA Palito (Blister c/ 4)", "UVV-ELE-01", "pct", "Para controles remotos de ar condicionado e laser", 30, 12, 1), # Abaixo do mínimo!

            # Entidade 3 - Logística & Distribuição Serra (Armazém / Embalagem / EPI)
            (19, 3, "Fita Adesiva Transparente 48mm x 100m", "LOG-EMB-01", "rolo", "Fita larga para fechamento de caixas pesadas", 50, 120, 1),
            (20, 3, "Filme Stretch Manual 500mm x 0,25mm", "LOG-EMB-02", "bobina", "Bobina de 3.5kg para paletização de cargas", 20, 15, 1), # Abaixo do mínimo!
            (21, 3, "Estilete Profissional com Trava 18mm", "LOG-FER-01", "un", "Estilete reforçado para corte de caixas e filmes", 15, 30, 1),
            (22, 3, "Luva de Proteção Pu Tátil Tamanho G", "LOG-EPI-01", "par", "Luva tricotada banhada em poliuretano na palma", 40, 85, 1),
            (23, 3, "Etiqueta Térmica Adesiva 100x150mm", "LOG-ETI-01", "rolo", "Rolo com 500 etiquetas para envio e despacho", 30, 22, 1),

            # Entidade 4 - Hospital Santa Maria (Saúde / Insumos / Descartáveis)
            (24, 4, "Luva de Procedimento Nitrílica M", "HOSP-001", "cx", "Caixa com 100 luvas sem pó na cor azul", 100, 250, 1),
            (25, 4, "Máscara Descartável Cirúrgica Tripla", "HOSP-002", "cx", "Caixa com 50 máscaras descartáveis com elástico", 80, 180, 1),
            (26, 4, "Álcool em Gel 70% com Dosador 500ml", "HOSP-003", "frasco", "Frasco com pump para bancadas e leitos", 50, 35, 1), # Abaixo do mínimo!
            (27, 4, "Avental Descartável Manga Longa Gr30", "HOSP-004", "pct", "Pacote com 10 aventais TNT hospitalares", 40, 20, 1), # Abaixo do mínimo!
            (28, 4, "Seringa Descartável 10ml com Agulha", "HOSP-005", "cx", "Caixa com 100 seringas bico luer slip", 60, 110, 1),

            # Entidade 5 - Indústria & Manutenção Cariacica (Ferramentas / Elétrica)
            (29, 5, "Fita Isolante 3M Scotch 20 Metros", "IND-ELE-01", "un", "Fita isolante antichama classe A até 750V", 30, 70, 1),
            (30, 5, "Óleo Lubrificante Spray WD-40 300ml", "IND-MAN-01", "lata", "Spray desengripante e protetivo antiferrugem", 20, 14, 1), # Abaixo do mínimo!
            (31, 5, "Abraçadeira de Nylon 200x3.6mm Preto", "IND-ELE-02", "pct", "Pacote com 100 abraçadeiras tipo enforca-gato", 25, 60, 1),
            (32, 5, "Óculos de Proteção Incolor Antirrisco", "IND-EPI-01", "un", "Óculos de segurança com proteção UV", 20, 18, 1),
        ]

        cur.executemany("""
            INSERT INTO suprimento (id, entidade_id, nome, codigo_interno, unidade_medida, descricao, estoque_minimo, estoque_atual, status, criado_em, atualizado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """, suprimentos_dados)

        # =========================================================================
        # 4. SOLICITAÇÕES DE RECURSOS (Processos em Andamento e Históricos)
        # =========================================================================
        print("[+] Gerando solicitações em andamento (Solicitada, Aprovada, Aguardando Estoque, Separada, Entregue)...")

        # Configuração das solicitações para criar um cenário rico
        solicitacoes_cenarios = [
            # 1. SOLICITADA (Aguardando Validação)
            {
                "entidade_id": 1, "solicitante_id": 10, "status": "solicitada",
                "observacao": "Solicitação mensal de materiais para o setor de faturamento e contas a pagar.",
                "itens": [(7, 4), (8, 2), (9, 3)], # Sulfite, Canetas, Post-it
                "dias_atras": 1, "validador_id": None, "entrega_id": None
            },
            {
                "entidade_id": 1, "solicitante_id": 11, "status": "solicitada",
                "observacao": "Cabos e conectores para cabeamento estruturado da nova sala de reuniões.",
                "itens": [(1, 1), (2, 2)], # Cabo de rede, Conector RJ45
                "dias_atras": 0, "validador_id": None, "entrega_id": None
            },
            {
                "entidade_id": 2, "solicitante_id": 15, "status": "solicitada",
                "observacao": "Reposição de papéis e marcadores para início das bancas examinadoras.",
                "itens": [(13, 5), (14, 3)],
                "dias_atras": 1, "validador_id": None, "entrega_id": None
            },
            {
                "entidade_id": 4, "solicitante_id": 24, "status": "solicitada",
                "observacao": "Solicitação urgente de luvas cirúrgicas e máscaras para a ala de pronto socorro.",
                "itens": [(24, 15), (25, 10)],
                "dias_atras": 0, "validador_id": None, "entrega_id": None
            },

            # 2. APROVADA (Pronta para Separação no Compilado Operacional)
            {
                "entidade_id": 1, "solicitante_id": 6, "status": "aprovada",
                "observacao": "Reposição de café e insumos de limpeza para copa do segundo andar.",
                "itens": [(10, 2), (11, 4), (12, 3)],
                "dias_atras": 2, "validador_id": 4, "entrega_id": None
            },
            {
                "entidade_id": 2, "solicitante_id": 16, "status": "aprovada",
                "observacao": "Substituição de mouses quebrados no Laboratório 3 de Ciência da Computação.",
                "itens": [(17, 8)],
                "dias_atras": 2, "validador_id": 12, "entrega_id": None
            },
            {
                "entidade_id": 3, "solicitante_id": 20, "status": "aprovada",
                "observacao": "Fitas e estiletes para embalagem de remessa especial para filial.",
                "itens": [(19, 12), (21, 4)],
                "dias_atras": 3, "validador_id": 18, "entrega_id": None
            },
            {
                "entidade_id": 5, "solicitante_id": 29, "status": "aprovada",
                "observacao": "Fitas isolantes e abraçadeiras para reforma do painel elétrico da prensa 02.",
                "itens": [(29, 6), (31, 3)],
                "dias_atras": 1, "validador_id": 27, "entrega_id": None
            },

            # 3. AGUARDANDO_ESTOQUE (Separada Parcialmente, Aguarda Reposição)
            {
                "entidade_id": 1, "solicitante_id": 11, "status": "aguardando_estoque",
                "observacao": "Teclados e mouses para montagem dos novos postos de atendimento.",
                "itens": [(3, 8, 4), (4, 8, 4)], # Solicitou 8, atendeu 4 de cada (parcial)
                "dias_atras": 4, "validador_id": 4, "entrega_id": None
            },
            {
                "entidade_id": 2, "solicitante_id": 16, "status": "aguardando_estoque",
                "observacao": "Cabos HDMI para os auditórios 01 e 02.",
                "itens": [(16, 8, 3)], # Solicitou 8, atendeu 3 (parcial)
                "dias_atras": 5, "validador_id": 12, "entrega_id": None
            },
            {
                "entidade_id": 4, "solicitante_id": 25, "status": "aguardando_estoque",
                "observacao": "Aventais descartáveis para equipe do centro cirúrgico ambulatorial.",
                "itens": [(27, 20, 10)], # Solicitou 20, atendeu 10
                "dias_atras": 3, "validador_id": 22, "entrega_id": None
            },

            # 4. SEPARADA (Pronta para entrega / Solicitante confirmar recebimento)
            {
                "entidade_id": 1, "solicitante_id": 2, "status": "separada", # Michel Salles como solicitante
                "observacao": "Toners e papéis especiais para impressão de relatórios de diretoria.",
                "itens": [(6, 2, 2), (7, 3, 3)],
                "dias_atras": 3, "validador_id": 4, "entrega_id": None
            },
            {
                "entidade_id": 3, "solicitante_id": 20, "status": "separada",
                "observacao": "Luvas táteis e estiletes para os novos operadores do turno da noite.",
                "itens": [(21, 5, 5), (22, 10, 10)],
                "dias_atras": 2, "validador_id": 18, "entrega_id": None
            },
            {
                "entidade_id": 5, "solicitante_id": 29, "status": "separada",
                "observacao": "Sprays desengripantes e óculos de proteção para manutenção preventiva.",
                "itens": [(30, 4, 4), (32, 6, 6)],
                "dias_atras": 2, "validador_id": 27, "entrega_id": None
            },

            # 5. ENTREGUE (Concluídas com Sucesso - Histórico Completo)
            {
                "entidade_id": 1, "solicitante_id": 10, "status": "entregue",
                "observacao": "Kit mensal de papelaria e suprimentos administrativos de rotina.",
                "itens": [(7, 6, 6), (8, 4, 4), (9, 5, 5)],
                "dias_atras": 12, "validador_id": 4, "entrega_id": 5
            },
            {
                "entidade_id": 1, "solicitante_id": 11, "status": "entregue",
                "observacao": "SSDs para upgrade de máquinas do departamento comercial.",
                "itens": [(5, 4, 4)],
                "dias_atras": 15, "validador_id": 4, "entrega_id": 5
            },
            {
                "entidade_id": 2, "solicitante_id": 15, "status": "entregue",
                "observacao": "Pilhas e apagadores para o bloco acadêmico C.",
                "itens": [(15, 6, 6), (18, 10, 10)],
                "dias_atras": 10, "validador_id": 12, "entrega_id": 14
            },
            {
                "entidade_id": 4, "solicitante_id": 24, "status": "entregue",
                "observacao": "Seringas e luvas de procedimento para o ambulatório geral.",
                "itens": [(24, 25, 25), (28, 15, 15)],
                "dias_atras": 8, "validador_id": 22, "entrega_id": 23
            },

            # 6. REJEITADA
            {
                "entidade_id": 1, "solicitante_id": 6, "status": "rejeitada",
                "observacao": "Solicitação extraordinária de 20 teclados mecânicos para testes.",
                "justificativa": "Pedido rejeitado pois não há previsão orçamentária para este tipo de equipamento neste trimestre.",
                "itens": [(3, 20)],
                "dias_atras": 6, "validador_id": 4, "entrega_id": None
            },

            # 7. CANCELADA
            {
                "entidade_id": 3, "solicitante_id": 20, "status": "cancelada",
                "observacao": "Bobinas de filme stretch para evento externo.",
                "justificativa": "Solicitação cancelada pelo próprio solicitante devido ao cancelamento do evento.",
                "itens": [(20, 5)],
                "dias_atras": 7, "validador_id": None, "entrega_id": None
            }
        ]

        solicitacao_id_counter = 1
        for c in solicitacoes_cenarios:
            dt_criacao = agora - timedelta(days=c["dias_atras"], hours=random.randint(1, 8))
            dt_validacao = dt_criacao + timedelta(hours=3) if c["validador_id"] else None
            dt_entrega = dt_validacao + timedelta(hours=5) if c["entrega_id"] else None

            cur.execute("""
                INSERT INTO solicitacao
                    (id, entidade_id, solicitante_id, status, observacao, justificativa_rejeicao,
                     validador_id, data_validacao, responsavel_entrega_id, data_entrega, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                solicitacao_id_counter,
                c["entidade_id"],
                c["solicitante_id"],
                c["status"],
                c["observacao"],
                c.get("justificativa"),
                c["validador_id"],
                dt_validacao,
                c["entrega_id"],
                dt_entrega,
                dt_criacao,
                dt_entrega or dt_validacao or dt_criacao
            ))

            # Insere itens
            for item in c["itens"]:
                sup_id = item[0]
                qtd_sol = item[1]
                qtd_atend = item[2] if len(item) > 2 else (qtd_sol if c["status"] in ("separada", "entregue") else 0)

                if qtd_atend >= qtd_sol:
                    status_item = "atendido" if c["status"] == "entregue" else "separado"
                elif qtd_atend > 0:
                    status_item = "separado"
                elif c["status"] == "aprovada":
                    status_item = "aprovado"
                elif c["status"] in ("rejeitada", "cancelada"):
                    status_item = "cancelado"
                else:
                    status_item = "pendente"

                cur.execute("""
                    INSERT INTO item_solicitacao
                        (solicitacao_id, suprimento_id, quantidade_solicitada, quantidade_atendida, status)
                    VALUES (%s, %s, %s, %s, %s)
                """, (solicitacao_id_counter, sup_id, qtd_sol, qtd_atend, status_item))

            # Registra Histórico de Eventos da Solicitação
            cur.execute("""
                INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao, criado_em)
                VALUES (%s, %s, NULL, 'solicitada', 'Solicitação aberta pelo usuário com os suprimentos requeridos', %s)
            """, (solicitacao_id_counter, c["solicitante_id"], dt_criacao))

            if c["validador_id"]:
                novo_st = "rejeitada" if c["status"] == "rejeitada" else "aprovada"
                desc = f"Solicitação rejeitada: {c.get('justificativa')}" if c["status"] == "rejeitada" else "Solicitação analisada e aprovada pelo gestor responsável."
                cur.execute("""
                    INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao, criado_em)
                    VALUES (%s, %s, 'solicitada', %s, %s, %s)
                """, (solicitacao_id_counter, c["validador_id"], novo_st, desc, dt_validacao))

            if c["status"] in ("aguardando_estoque", "separada", "entregue"):
                dt_sep = dt_validacao + timedelta(hours=2) if dt_validacao else dt_criacao
                st_sep = "aguardando_estoque" if c["status"] == "aguardando_estoque" else "separada"
                desc_sep = "Separação física parcial realizada. Aguardando reposição de estoque." if st_sep == "aguardando_estoque" else "Separação física de todos os itens concluída no almoxarifado."
                cur.execute("""
                    INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao, criado_em)
                    VALUES (%s, %s, 'aprovada', %s, %s, %s)
                """, (solicitacao_id_counter, c["validador_id"] or 1, st_sep, desc_sep, dt_sep))

            if c["status"] == "entregue":
                cur.execute("""
                    INSERT INTO historico_solicitacao (solicitacao_id, usuario_id, estado_anterior, estado_novo, descricao, criado_em)
                    VALUES (%s, %s, 'separada', 'entregue', 'Itens entregues ao solicitante com sucesso. Atendimento concluído.', %s)
                """, (solicitacao_id_counter, c["entrega_id"], dt_entrega))

            solicitacao_id_counter += 1

        # =========================================================================
        # 5. PEDIDOS DE COMPRA (Reposição de Estoque)
        # =========================================================================
        print("[+] Criando pedidos de compra de demonstração...")
        # Status possíveis: 'em_montagem', 'aguardando_cotacao', 'pedido_realizado', 'parcialmente_recebido', 'recebido', 'cancelado'
        pedidos_cenarios = [
            {
                "id": 1, "entidade_id": 1, "usuario_id": 4, # Gerente Matriz
                "nome": "Reposição Periféricos e Toners - Junho",
                "status": "pedido_realizado",
                "observacao": "Pedido urgente para recompor estoque de toners e teclados em nível crítico.",
                "itens": [
                    (3, 20, 20, 0), # Teclados: necessita 20, pediu 20, recebeu 0
                    (4, 20, 20, 0), # Mouses: necessita 20, pediu 20, recebeu 0
                    (6, 10, 10, 0), # Toners: necessita 10, pediu 10, recebeu 0
                ]
            },
            {
                "id": 2, "entidade_id": 1, "usuario_id": 2, # Michel Salles
                "nome": "Aquisição Suprimentos Copa e Papelaria Trimestral",
                "status": "parcialmente_recebido",
                "observacao": "Entrega parcial realizada pela distribuidora. Aguardando restante.",
                "itens": [
                    (7, 50, 50, 50), # Papel Sulfite: recebeu 50
                    (9, 30, 30, 15), # Post-it: recebeu 15 de 30
                    (11, 40, 40, 20), # Café: recebeu 20 de 40
                ]
            },
            {
                "id": 3, "entidade_id": 1, "usuario_id": 4,
                "nome": "Compra Emergencial Álcool e Higiene",
                "status": "recebido",
                "observacao": "Pedido finalizado e insumos já incorporados ao saldo de estoque.",
                "itens": [
                    (10, 30, 30, 30), # Álcool: recebeu tudo
                    (12, 25, 25, 25), # Papel toalha: recebeu tudo
                ]
            },
            {
                "id": 4, "entidade_id": 1, "usuario_id": 5, # Gestor
                "nome": "Cotação Cabos e Conectores de Rede",
                "status": "aguardando_cotacao",
                "observacao": "Em cotação com 3 fornecedores locais para melhor preço em bobinas de cabo.",
                "itens": [
                    (1, 10, 10, 0),
                    (2, 20, 20, 0),
                ]
            },
            {
                "id": 5, "entidade_id": 2, "usuario_id": 12, # Bruno Torres UVV
                "nome": "Reposição de Cabos HDMI e Pilhas - Salas de Aula",
                "status": "pedido_realizado",
                "observacao": "Fornecedor confirmou faturamento e entrega prevista para 3 dias.",
                "itens": [
                    (16, 15, 15, 0),
                    (18, 40, 40, 0),
                ]
            },
            {
                "id": 6, "entidade_id": 3, "usuario_id": 18, # Gerente Logística Serra
                "nome": "Compra de Filme Stretch e Fitas de Embalagem",
                "status": "em_montagem",
                "observacao": "Identificação de demanda para o próximo mês de alta temporada logística.",
                "itens": [
                    (19, 100, 0, 0),
                    (20, 30, 0, 0),
                ]
            },
            {
                "id": 7, "entidade_id": 4, "usuario_id": 22, # Gerente Hospital
                "nome": "Insumos Hospitalares de Emergência e Descartáveis",
                "status": "recebido",
                "observacao": "Lote recebido com laudo técnico e nota fiscal conferida.",
                "itens": [
                    (24, 200, 200, 200),
                    (26, 60, 60, 60),
                ]
            }
        ]

        for ped in pedidos_cenarios:
            cur.execute("""
                INSERT INTO pedido_compra (id, entidade_id, usuario_id, nome, status, observacao, criado_em, atualizado_em)
                VALUES (%s, %s, %s, %s, %s, %s, NOW() - INTERVAL 5 DAY, NOW())
            """, (ped["id"], ped["entidade_id"], ped["usuario_id"], ped["nome"], ped["status"], ped["observacao"]))

            for it in ped["itens"]:
                cur.execute("""
                    INSERT INTO item_pedido_compra (pedido_id, suprimento_id, quantidade_necessaria, quantidade_pedida, quantidade_recebida)
                    VALUES (%s, %s, %s, %s, %s)
                """, (ped["id"], it[0], it[1], it[2], it[3]))

        # =========================================================================
        # 6. HISTÓRICO DE MOVIMENTAÇÕES DE ESTOQUE (Auditoria Imutável)
        # =========================================================================
        print("[+] Criando histórico de movimentações de estoque (entradas e saídas)...")
        # Tipos permitidos no enum: 'entrada', 'saida', 'ajuste', 'transferencia'
        movimentacoes = [
            # Entradas de pedidos recebidos
            (1, 10, "entrada", 30, 0, 30, None, 4, "Recebimento do Pedido de Compra #3 - Lote NF 88321", agora - timedelta(days=6)),
            (1, 12, "entrada", 25, 0, 25, None, 4, "Recebimento do Pedido de Compra #3 - Lote NF 88321", agora - timedelta(days=6)),
            (1, 7,  "entrada", 50, 10, 60, None, 2, "Recebimento Parcial Pedido #2 - Michel Salles", agora - timedelta(days=4)),
            (1, 11, "entrada", 20, 15, 35, None, 2, "Recebimento Parcial Pedido #2 - Café", agora - timedelta(days=4)),
            (4, 24, "entrada", 200, 50, 250, None, 22, "Recebimento Pedido #7 - Luvas Nitrílicas Hospitalares", agora - timedelta(days=5)),

            # Saídas para solicitações entregues ou separadas
            (1, 7,  "saida", 6, 60, 54, 15, 5, "Separação para Solicitação #15 - Setor Faturamento", agora - timedelta(days=12)),
            (1, 8,  "saida", 4, 29, 25, 15, 5, "Separação para Solicitação #15 - Canetas", agora - timedelta(days=12)),
            (1, 5,  "saida", 4, 18, 14, 16, 5, "Separação para Solicitação #16 - SSDs Comercial", agora - timedelta(days=15)),
            (1, 3,  "saida", 4, 12, 8, 9, 5, "Separação parcial Solicitação #9 - Novos Postos", agora - timedelta(days=4)),
            (1, 4,  "saida", 4, 10, 6, 9, 5, "Separação parcial Solicitação #9 - Mouses", agora - timedelta(days=4)),
            (1, 6,  "saida", 2, 5, 3, 12, 5, "Separação para Solicitação #12 - Michel Salles", agora - timedelta(days=3)),

            # Ajustes de inventário
            (1, 1,  "ajuste", 2, 10, 12, None, 4, "Ajuste de conferência física de prateleira Almoxarifado Central", agora - timedelta(days=20)),
            (2, 13, "ajuste", 5, 55, 60, None, 12, "Inventário semestral Campus Boa Vista", agora - timedelta(days=18)),
        ]

        cur.executemany("""
            INSERT INTO movimentacao_estoque
                (entidade_id, suprimento_id, tipo, quantidade, quantidade_anterior, quantidade_posterior,
                 solicitacao_id, usuario_id, observacao, criado_em)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, movimentacoes)

    print("\n=========================================================================")
    print("✓ BANCO DE DADOS POPULADO COM SUCESSO COM DADOS DE DEMONSTRAÇÃO!")
    print("=========================================================================")
    print("Empresas Cadastradas:")
    print("  1. Estok Matriz (Vitória)")
    print("  2. UVV - Campus Boa Vista")
    print("  3. Logística & Distribuição Serra")
    print("  4. Hospital Santa Maria")
    print("  5. Indústria & Manutenção Cariacica")
    print("\nCredenciais de Demonstração (SENHA DE TODOS = 123):")
    print("  - Super-Admin:     login = admin         | senha = 123")
    print("  - Michel Salles:   login = michel.salles | senha = 123")
    print("  - Gerente Matriz:  login = gerente       | senha = 123")
    print("  - Gestor Matriz:   login = gestor        | senha = 123")
    print("  - Solicitante:     login = solicitante   | senha = 123")
    print("  - Admin Entidade:  login = admin.entidade| senha = 123")
    print("  - Gerente UVV:     login = bruno.torres  | senha = 123")
    print("=========================================================================")


if __name__ == "__main__":
    semeando = semear_dados()

