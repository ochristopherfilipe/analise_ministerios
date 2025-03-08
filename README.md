# Avaliação dos Ministérios

Uma aplicação Streamlit para facilitar a avaliação mensal dos ministérios, permitindo que líderes preencham formulários e a gestora visualize análises.

## Funcionalidades

### Para os Líderes de Ministério
- Formulário completo para avaliação mensal
- Seções detalhadas para avaliar diversos aspectos do ministério
- Validação de dados para garantir entrada correta
- Sistema de envio seguro para o banco de dados

### Para a Gestora dos Ministérios
- Área protegida por login (Usuário: EDILENE SANTOS, Senha: PASTORAEDILENE)
- Visualização da classificação geral dos ministérios
- Gráficos detalhados para cada ministério
- Filtros por mês e ano para análise temporal

## Requisitos

- Python 3.7 ou superior
- Todas as dependências listadas no arquivo `requirements.txt`

## Instalação

1. Clone o repositório ou baixe os arquivos do projeto
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

## Execução

Para iniciar a aplicação, execute o seguinte comando no diretório do projeto:

```bash
streamlit run app.py
```

A aplicação será aberta no seu navegador padrão, geralmente no endereço `http://localhost:8501`.

## Estrutura do Banco de Dados

A aplicação utiliza um banco de dados PostgreSQL hospedado no Supabase para armazenar as avaliações dos ministérios. A tabela principal, `avaliacoes_ministerios`, contém os seguintes campos:

- Informações básicas: ministério, nome do líder, email
- Avaliações numéricas (1-10): pontualidade, assiduidade, trabalho em equipe
- Descrições das atividades semanais
- Treinamentos e estratégias
- Dados sobre novos membros
- Comentários e sugestões
- Informações de data e período de referência

## Suporte

Para dúvidas ou problemas, entre em contato com o administrador do sistema. 