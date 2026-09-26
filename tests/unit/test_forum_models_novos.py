"""Novos testes unitários para o módulo flaskbb/forum — Tarefa 1.3.

Estes testes cobrem cenários que a suíte original não exercitava,
divididos entre caminhos felizes, casos de borda e situações de erro.
Cada teste é independente dos demais e pode rodar em qualquer ordem.
"""

import pytest
from flask import current_app

from flaskbb.extensions import db
from flaskbb.forum.models import Category, Forum, Post, Report, Topic


# ---------------------------------------------------------------------------
# Caminhos felizes
# ---------------------------------------------------------------------------


def test_topic_save_with_explicit_post(forum, user):
    """Ao criar um tópico passando um Post explicitamente pelo parâmetro
    'post=', esse post deve ser vinculado como primeiro e último post
    do tópico."""
    topic = Topic(title="Tópico com post explícito")
    post_externo = Post(content="Post criado fora do Topic.__init__")

    topic.save(forum=forum, user=user, post=post_externo)

    assert topic.first_post.content == "Post criado fora do Topic.__init__"


def test_report_save_sets_reporter_and_post(topic, user):
    """Quando um report é criado pela primeira vez (sem id),
    o método save() deve preencher automaticamente o reporter,
    a data de criação e o post denunciado."""
    report = Report(reason="Conteúdo ofensivo")
    report.save(user=user, post=topic.first_post)

    assert report.reporter == user
    assert report.post == topic.first_post
    assert report.reported is not None


def test_topic_init_with_content_creates_internal_post(user):
    """Ao instanciar um Topic com o parâmetro 'content', o construtor
    deve criar internamente um objeto Post acessível via _post."""
    topic = Topic(title="Tópico com conteúdo", user=user, content="Olá mundo")

    assert hasattr(topic, "_post")
    assert topic._post.content == "Olá mundo"


# ---------------------------------------------------------------------------
# Casos de borda
# ---------------------------------------------------------------------------


def test_delete_last_post_leaves_forum_without_last_post(forum, user):
    """Se o fórum tem um único tópico com um único post, e esse post é
    deletado (o que deleta o tópico inteiro), os campos de 'último post'
    do fórum devem ficar todos como None."""
    topic = Topic(title="Tópico solitário")
    post = Post(content="Único post")
    topic.save(forum=forum, user=user, post=post)

    topic.first_post.delete()

    assert forum.last_post is None
    assert forum.last_post_title is None
    assert forum.last_post_username is None


def test_hide_only_topic_clears_forum_last_post(forum, user):
    """Quando o fórum possui apenas um tópico e ele é escondido,
    todos os indicadores de 'último post' do fórum devem ser zerados."""
    topic = Topic(title="Tópico único")
    post = Post(content="Post único")
    topic.save(forum=forum, user=user, post=post)

    topic.hide(user)

    assert forum.last_post is None
    assert forum.last_post_title is None
    assert forum.last_post_created is None


def test_topic_second_last_post_with_single_post(forum, user):
    """Se um tópico possui apenas um post, a propriedade second_last_post
    deve retornar None, já que não existe um 'penúltimo'."""
    topic = Topic(title="Tópico simples")
    post = Post(content="Post único")
    topic.save(forum=forum, user=user, post=post)

    assert topic.second_last_post is None


# ---------------------------------------------------------------------------
# Cenários de erro
# ---------------------------------------------------------------------------


def test_topic_save_without_forum_returns_none(database):
    """Tentar salvar um tópico novo sem informar fórum nem usuário
    deve retornar None sem lançar exceção — o sistema apenas registra
    um log de erro."""
    topic = Topic(title="Tópico órfão", content="Sem destino")

    result = topic.save(forum=None, user=None)

    assert result is None


def test_get_topic_with_invalid_id_aborts_404(forum, user):
    """Buscar um tópico com um ID que não existe no banco deve
    disparar um erro HTTP 404."""
    with current_app.test_request_context():
        with pytest.raises(Exception) as excinfo:
            Topic.get_topic(topic_id=999999)

        # O abort(404) do Flask levanta um HTTPException com código 404
        assert hasattr(excinfo.value, "code") and excinfo.value.code == 404


def test_hide_already_hidden_post_does_nothing(topic, user):
    """Chamar hide() em um post que já está escondido não deve
    alterar nenhum contador — o método retorna imediatamente."""
    new_post = Post(content="Post para esconder duas vezes")
    new_post.save(user=user, topic=topic)

    new_post.hide(user)
    post_count_after_first_hide = topic.post_count
    forum_post_count_after_first_hide = topic.forum.post_count

    # Segunda chamada: não deve mudar nada
    new_post.hide(user)

    assert topic.post_count == post_count_after_first_hide
    assert topic.forum.post_count == forum_post_count_after_first_hide


def test_unhide_visible_post_does_nothing(topic, user):
    """Chamar unhide() em um post que não está escondido não deve
    causar nenhum efeito colateral."""
    new_post = Post(content="Post visível")
    new_post.save(user=user, topic=topic)

    post_count_before = topic.post_count

    # Tentar "des-esconder" um post que já está visível
    new_post.unhide()

    assert topic.post_count == post_count_before
    assert new_post.hidden is False


# ---------------------------------------------------------------------------
# Tarefa 1.4 — Teste parametrizado
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "title,         content,         has_user, expect_title,  expect_post, expect_user",
    [
        # Caso 1 (válido): todos os parâmetros preenchidos
        ("Meu tópico", "Olá mundo",     True,  "Meu tópico",  True,        True),

        # Caso 2 (válido): título e usuário, sem conteúdo
        ("Só título",   None,            True,  "Só título",   False,       True),

        # Caso 3 (válido): título e conteúdo, sem usuário
        ("Com texto",   "Algum texto",   False, "Com texto",   True,        False),

        # Caso 4 (borda): apenas título, sem usuário nem conteúdo
        ("Mínimo",      None,            False, "Mínimo",      False,       False),

        # Caso 5 (inválido): string vazia como título — tratada como falsy
        ("",            "Post órfão",    True,  None,          True,        True),

        # Caso 6 (inválido): nenhum parâmetro
        (None,          None,            False, None,          False,       False),
    ],
    ids=[
        "todos_preenchidos",
        "titulo_e_usuario",
        "titulo_e_conteudo",
        "apenas_titulo",
        "titulo_vazio",
        "nenhum_parametro",
    ],
)
def test_topic_init_parametrizado(
    title, content, has_user, expect_title, expect_post, expect_user, user, database
):
    """Verifica que o construtor de Topic se comporta corretamente
    para diferentes combinações de parâmetros: com e sem título,
    com e sem conteúdo, com e sem usuário."""
    topic_user = user if has_user else None
    topic = Topic(title=title, user=topic_user, content=content)

    # Título: só é atribuído se for uma string não-vazia
    if expect_title:
        assert topic.title == expect_title
    else:
        assert not hasattr(topic, "title") or topic.title is None

    # Post interno: só é criado quando content é fornecido
    if expect_post:
        assert hasattr(topic, "_post")
        assert topic._post.content == content
    else:
        assert not hasattr(topic, "_post")

    # Usuário: user_id e username são preenchidos apenas quando user é passado
    if expect_user:
        assert topic.user_id == user.id
        assert topic.username == user.username
    else:
        assert not hasattr(topic, "user_id") or topic.user_id is None

    # Em todos os casos, date_created deve ser preenchido
    assert topic.date_created is not None


# ---------------------------------------------------------------------------
# Tarefa 1.5 — Teste com dublê (mock)
# ---------------------------------------------------------------------------


def test_topic_save_dispatches_plugin_hooks(forum, user, mocker):
    """Ao salvar um tópico novo, o método save() deve notificar o sistema
    de plugins chamando os hooks 'before' e 'after' na ordem correta e
    com os argumentos esperados.

    O mock é necessário porque o sistema de plugins (pluggy) é uma
    dependência externa ao módulo forum. Sem o dublê, o teste dependeria
    de plugins reais estarem carregados, e não seria possível verificar
    se os hooks foram chamados com os argumentos corretos (ex.: is_new=True
    para tópico novo). O mock isola o forum do pluggy, permitindo focar
    no comportamento do save()."""

    # Substitui os hooks do pluggy por mocks
    mock_before = mocker.patch(
        "flaskbb.forum.models.pluggy.hook.flaskbb_event_topic_save_before"
    )
    mock_after = mocker.patch(
        "flaskbb.forum.models.pluggy.hook.flaskbb_event_topic_save_after"
    )
    # O Post.save() também chama hooks — precisamos mocká-los para não
    # interferir, mas o foco do teste é no Topic
    mocker.patch("flaskbb.forum.models.pluggy.hook.flaskbb_event_post_save_before")
    mocker.patch("flaskbb.forum.models.pluggy.hook.flaskbb_event_post_save_after")

    topic = Topic(title="Tópico com hooks")
    post = Post(content="Conteúdo do post")
    topic.save(forum=forum, user=user, post=post)

    # Verifica que o hook "before" foi chamado uma vez, passando o tópico
    mock_before.assert_called_once_with(topic=topic)

    # Verifica que o hook "after" foi chamado uma vez, com is_new=True
    # (porque é um tópico novo, não uma atualização)
    mock_after.assert_called_once_with(topic=topic, is_new=True)
