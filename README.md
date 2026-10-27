# Estok - Sistema de Gestão de Recursos e Estoque

Sistema monolítico de gestão de recursos, catálogo de suprimentos, solicitações internas e controle de estoque com suporte a **Multi-tenancy (múltiplas entidades/empresas)** e **Controle de Acesso Baseado em Perfis (RBAC)**.

---

## 🚀 Como Acessar o Ambiente

### 🔑 Acesso Rápido - Super-Administrador (Dono do Sistema)

Para acessar o sistema com o perfil **Super-Admin** (acesso universal irrestrito a todas as empresas, configurações e perfis):

* **URL de Login:** `http://127.0.0.1:5000/login`
* **Login:** `admin`
* **Senha:** `admin123`

> **Dica de Navegação:** O usuário `admin` possui todos os perfis associados. No canto superior direito da tela, clicando sobre o seu nome, você pode abrir o menu de **Perfil** para alternar a qualquer momento entre **Super-Admin**, **Administrador**, **Gerente**, **Gestor** ou **Solicitante**, visualizando a interface e restrições de cada perfil em tempo real. Além disso, no menu de **Entidade**, o Super-Admin pode transitar entre as entidades cadastradas ou optar pela **Visão Global (Todas as Entidades)**.

---

## 👥 Credenciais Pré-configuradas para Testes

Para facilitar a validação e avaliação dos fluxos de trabalho e permissões, os seguintes usuários padrão já vêm cadastrados no banco de dados:

| Perfil | Login | Senha | Entidade Vinculada | Escopo de Acesso |
| :--- | :--- | :--- | :--- | :--- |
| **Super-Admin** | `admin` | `admin123` | *Acesso Global* | Acesso total a todas as entidades, usuários e configurações da plataforma. |
| **Administrador** | `admin.entidade` | `admin123` | Estok Matriz | Gestão completa da sua entidade: Usuários da empresa, Suprimentos, Estoque, Pedidos e Solicitações. |
| **Gerente** | `gerente` | `gerente123` | Estok Matriz | Gestão de Suprimentos (CRUD), Pedidos de Compras, Estoque e validação de Solicitações. |
| **Gestor** | `gestor` | `gestor123` | Estok Matriz | Controle físico de Estoque, separação/entrega de itens, compilado operacional e consulta ao catálogo. |
| **Solicitante** | `solicitante` | `solicitante123` | Estok Matriz | Abertura e acompanhamento exclusivo das solicitações de suprimentos para o seu setor. |

---

## 📋 Matriz de Perfis e Permissões (UML)

O controle de permissões reflete fielmente as especificações e diagramas de caso de uso do projeto:

* **Solicitante:**
  * Cria solicitações de suprimentos para o seu departamento.
  * Consulta o histórico e status **exclusivamente das suas próprias solicitações**.
  * Cancela solicitações de sua autoria que ainda estejam pendentes de validação.
  * *Não possui acesso a Suprimentos, Estoque, Pedidos ou Administração.*

* **Gestor:**
  * Valida, aprova e rejeita solicitações de recursos.
  * Realiza a separação física de estoque e confirma a entrega dos suprimentos ao solicitante.
  * Acessa o **Compilado Operacional** para separação em lote.
  * Consulta o catálogo de Suprimentos (**somente-leitura**, sem permissão de cadastro/edição/exclusão).
  * Consulta saldos de estoque e histórico de movimentações.
  * *Não acessa Pedidos de Compras nem telas de Administração.*

* **Gerente:**
  * Gestão completa do Catálogo de Suprimentos (**Cadastrar, Editar, Inativar e Excluir**).
  * Gestão de **Pedidos de Compras** (montagem de pedido, cotação, inserção de itens e registro de recebimento).
  * Validação e aprovação de solicitações de recursos.
  * Consulta de saldos e movimentações de estoque.
  * *Não acessa telas de Administração de usuários/entidades.*

* **Administrador (Administrador da Entidade/Empresa):**
  * Perfil utilizado pelos administradores de cada empresa/entidade.
  * Possui controle operacional completo da sua unidade (Solicitações, Suprimentos, Estoque e Pedidos).
  * Acesso à tela de **Gestão de Usuários (`/admin/usuarios`)**, com escopo estritamente restrito à sua própria entidade (pode cadastrar operadores, gerentes, gestores e solicitantes da sua entidade, não podendo conceder perfil Super-Admin).
  * *Não possui acesso à Gestão de Entidades (`/admin/entidades`), que é exclusiva dos donos da plataforma.*

* **Super-Admin:**
  * Dono do sistema e responsável pelo gerenciamento global.
  * Gestão de Entidades (**Cadastrar, Editar e Inativar empresas clientes**).
  * Gestão de Usuários globais e atribuição de qualquer perfil.
  * Seletor de contexto para transitar entre dados de qualquer entidade ou consultar a visão agregada.

---

## 🛠️ Tecnologias Utilizadas

* **Linguagem:** Python 3.10+
* **Framework Web:** Flask (com Jinja2 Templates)
* **Banco de Dados:** MySQL 8.0+ (Driver PyMySQL)
* **Segurança:** Hashing de senhas com `werkzeug.security` (Scrypt), proteção de rotas com decorators e isolamento multi-tenant por entidade.
* **Estilização:** CSS moderno e responsivo com paleta corporativa e suporte a transição de menus flyout.

---

## ⚙️ Pré-requisitos e Instalação

### 1. Clonar o repositório
```bash
git clone https://github.com/Vr6Bruno/Trabalho-Grupo-2.git
cd Trabalho-Grupo-2
```

### 2. Criar e ativar o ambiente virtual (Recomendado)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto (ou copie a partir do `.env.example`):
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=estok
SECRET_KEY=sua_chave_secreta_aqui
```

### 5. Inicializar o Banco de Dados MySQL
Certifique-se de que o serviço MySQL esteja em execução. Em seguida, crie o banco `estok` e execute a inicialização automática do schema e dados padrão:

```sql
CREATE DATABASE IF NOT EXISTS estok CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Execute o script de inicialização do projeto:
```bash
python database/init_db.py
```
*(O script criará todas as tabelas, índices relacionais e fará o seed automático dos perfis e usuários padrão).*

### 6. Executar a Aplicação
```bash
python app.py
```
A aplicação estará disponível em `http://127.0.0.1:5000`.

---

## 📦 Estrutura de Diretórios

```text
estok/
├── app/
│   ├── models/            # Modelos e regras de negócio com queries parametrizadas
│   │   ├── entidade.py
│   │   ├── estoque.py
│   │   ├── pedido.py
│   │   ├── solicitacao.py
│   │   ├── suprimento.py
│   │   └── usuario.py
│   ├── routes/            # Blueprints e controladores das rotas
│   │   ├── admin.py       # Gestão de Entidades e Usuários
│   │   ├── auth.py        # Login, Logout e troca de Perfil/Entidade
│   │   ├── estoque.py     # Saldos, histórico e relatório consolidado
│   │   ├── pedidos.py     # Pedidos de compra e recebimentos
│   │   ├── solicitacoes.py# Ciclo de vida e separação de solicitações
│   │   └── suprimentos.py # Catálogo de suprimentos
│   ├── static/css/        # Folhas de estilo da interface
│   ├── templates/         # Templates HTML (Jinja2) organizados por módulo
│   ├── auth.py            # Decorators de controle de acesso (RBAC)
│   ├── config.py          # Carregamento de configurações e variáveis de ambiente
│   └── db.py              # Gerenciador de conexão com o banco MySQL
├── database/
│   ├── init_db.py         # Script Python de inicialização/migração do banco
│   └── schema.sql         # Script SQL com DDL completo e seeds
├── documentos/            # Documentação de requisitos, UMLs e conceitos
├── app.py                 # Ponto de entrada da aplicação
├── requirements.txt       # Dependências do projeto
└── README.md              # Guia e documentação do projeto
```
