from __future__ import annotations

from aurora.tools.capitulos import consultar_regulamento


def test_piscina_domingo_traz_horario_de_fechamento():
    resultado = consultar_regulamento("piscina")
    assert resultado["encontrado"] is True
    assert "20h" in resultado["texto"]


def test_devolve_um_capitulo_so_nunca_o_documento_inteiro():
    resultado = consultar_regulamento("piscina")
    # capítulos vizinhos não podem vazar junto
    assert "Capítulo III" not in resultado["texto"]
    assert "Capítulo V" not in resultado["texto"]
    assert "Academia" not in resultado["texto"]


def test_assunto_desconhecido_nao_inventa_e_lista_opcoes():
    resultado = consultar_regulamento("assunto-que-nao-existe-xyz")
    assert resultado["encontrado"] is False
    assert "texto" not in resultado
    assert len(resultado["assuntos_disponiveis"]) > 0


def test_animais_e_garagem_capitulos_distintos():
    animais = consultar_regulamento("animais")
    garagem = consultar_regulamento("garagem")
    assert animais["capitulo"] != garagem["capitulo"]
