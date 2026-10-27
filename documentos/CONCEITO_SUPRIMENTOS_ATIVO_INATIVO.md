# Conceito de Suprimentos: Ativo vs. Inativo

Este documento detalha a regra de negócio e o ciclo de vida dos suprimentos no sistema **Estok**, em conformidade com o requisito **RN-12** do Documento de Especificação de Requisitos.

---

## 1. Contexto e Motivação
Em sistemas de controle de estoque e recursos operacionais, a exclusão física (`DELETE FROM suprimento`) de um item que já participou de movimentações, solicitações ou relatórios passados causa **quebra de integridade referencial** e perda de rastreabilidade contábil e operacional.

Por esse motivo, o sistema adota a estratégia de **exclusão lógica (*Soft Delete*)** por meio do campo booleano `status`:
- `status = 1` ➔ **Ativo**
- `status = 0` ➔ **Inativo**

---

## 2. Definição dos Estados

### 🟢 Suprimento Ativo (`status = 1`)
* **Disponibilidade no Catálogo:** O item é listado no catálogo oficial da entidade para seleção em novas solicitações de recursos por parte dos solicitantes.
* **Controle de Saldo:** Possui estoque atual e estoque mínimo monitorados ativamente pelo sistema.
* **Alertas de Nível Crítico:** Quando o `estoque_atual <= estoque_minimo`, o sistema sinaliza visualmente o card e a linha da tabela como **Crítico** para ação rápida do Gerente ou Estoquista.
* **Movimentações:** Permite registros rotineiros de entrada, saída, ajustes e separações de pedidos.

### ⚪ Suprimento Inativo (`status = 0`)
* **Bloqueio para Novas Requisições:** O item **não aparece** como opção no formulário de criação de novas solicitações. Solicitantes não conseguem pedir itens inativos.
* **Preservação Histórica:** Todos os registros anteriores de movimentações de estoque, atendimentos e relatórios contábeis permanecem 100% íntegros e auditáveis.
* **Visibilidade Administrativa:** Gerentes e Administradores conseguem consultar os itens inativos através do filtro `Status: Inativos` na tela de catálogo.
* **Reversibilidade:** Caso o suprimento volte a ser comercializado ou estocado, o Gerente pode editar o item e alterar seu status de volta para **Ativo**, restaurando imediatamente sua disponibilidade sem necessidade de recadastrá-lo.

---

## 3. Resumo Operacional

| Operação | Suprimento Ativo | Suprimento Inativo |
| :--- | :---: | :---: |
| Visível no Catálogo Geral (Gerente) | Sim | Sim (via filtro) |
| Disponível para Novas Solicitações | **Sim** | **Não (Bloqueado)** |
| Movimentações de Entrada/Saída | Sim | Bloqueado / Apenas histórico |
| Gera alertas de Estoque Crítico | Sim | Não |
| Pode ser Reativado | N/A | **Sim (pelo Gerente)** |
