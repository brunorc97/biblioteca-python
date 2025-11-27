import csv
import os

from db import conectar

DATA_DIR = "dados_biblioteca"
os.makedirs(DATA_DIR, exist_ok=True)

def salvar_csv(nome_arquivo, dados, campos):
    with open(os.path.join(DATA_DIR, nome_arquivo), mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(dados)

def carregar_csv(nome_arquivo, campos):
    caminho = os.path.join(DATA_DIR, nome_arquivo)
    if os.path.exists(caminho):
        with open(caminho, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    return []
import flet as ft

# Listas globais para armazenar os dados
emprestimos = []
avaliacoesLivros = []
avaliacoesBiblioteca = []

def main(page: ft.Page):
    global emprestimos, avaliacoesLivros, avaliacoesBiblioteca
    conn = conectar()
    print("Conectando ao banco...")
    if conn.is_connected():
        print("Conectado com sucesso ao MySQL!")
    else:
        print("Falha na conexão com o MySQL.")
    cursor = conn.cursor(dictionary=True)

    # Remove duplicados na tabela livros (mantendo o registro mais recente para cada título)
    try:
        cursor.execute("""
            DELETE l1 FROM livros l1
            JOIN livros l2 
            ON l1.titulo = l2.titulo AND l1.id_livro > l2.id_livro
        """)
        conn.commit()
    except Exception as ex:
        print("Erro ao remover duplicados em livros:", ex)

    # Garante que a coluna quantidade_ativo existe na tabela livros
    try:
        cursor.execute("SHOW COLUMNS FROM livros LIKE 'quantidade_ativo';")
        coluna_existe = cursor.fetchone()
        if not coluna_existe:
            cursor.execute("ALTER TABLE livros ADD COLUMN quantidade_ativo INT DEFAULT 0;")
            conn.commit()
    except Exception as ex:
        print("Erro ao adicionar coluna quantidade_ativo:", ex)

    # Carrega alunos diretamente do banco
    cursor.execute("SELECT nome FROM alunos ORDER BY nome;")
    alunos = [row["nome"] for row in cursor.fetchall()]

    # Carrega livros diretamente do banco (apenas disponíveis para empréstimo)
    cursor.execute("SELECT titulo, disponibilidade FROM livros ORDER BY titulo;")
    livros = [f"{row['titulo']} (Indisponível no momento)" if row['disponibilidade'] == 0 else row['titulo'] for row in cursor.fetchall()]

    # Carrega empréstimos do banco
    cursor.execute("""
        SELECT l.titulo AS livro, a.nome AS aluno, DATE_FORMAT(e.data_retirada, '%d/%m/%Y') AS data
        FROM emprestimos e
        JOIN livros l ON e.id_livro = l.id_livro
        JOIN alunos a ON e.id_aluno = a.id_aluno
    """)
    emprestimos = cursor.fetchall()

    # Carrega avaliações de livros
    cursor.execute("""
        SELECT a.nome AS usuario, l.titulo AS livro, av.nota, av.comentario
        FROM avaliacoes av
        JOIN livros l ON av.id_livro = l.id_livro
        JOIN alunos a ON av.id_aluno = a.id_aluno
    """)
    avaliacoesLivros = cursor.fetchall()

    # Carrega avaliações de atendimento (se existir tabela)
    try:
        cursor.execute("""
            SELECT a.nome AS usuario, aa.nota, aa.comentario
            FROM avaliacoes_atendimento aa
            JOIN alunos a ON aa.id_aluno = a.id_aluno
        """)
        avaliacoesBiblioteca = cursor.fetchall()
    except:
        avaliacoesBiblioteca = []

    conn.close()
    page.theme = ft.Theme()
    page.theme.font_family = "Poppins"
    page.title = "Gerenciamento de Biblioteca"
    page.window_width = 600
    page.window_height = 500
    page.bgcolor = "#007AFF"
    page.session.set("tema_botao", "#007AFF")
    page.session.set("tema_container", "white")
    page.padding = 20
    # Tema claro/escuro
    page.theme_mode = ft.ThemeMode.LIGHT
    page.update()

    # Dialog global para feedback visual
    dialog = ft.AlertDialog(
        title=ft.Text("Sucesso"),
        content=ft.Text("Operação concluída com sucesso!"),
        actions=[ft.TextButton("OK", on_click=lambda _: fechar_dialog())],
    )
    def fechar_dialog():
        dialog.open = False
        page.update()

    def cor_texto():
        return "#FFFFFF" if page.theme_mode == ft.ThemeMode.DARK else "#1C1C1E"

    def criar_botao(texto, on_click, cor_fundo=None):
        if not cor_fundo:
            # Primary: blue in light, dark gray in dark mode. But now, default gray in light mode is light gray.
            cor_fundo = "#3A3A3C" if page.theme_mode == ft.ThemeMode.DARK else "#E0E0E0"
        # Set text color: white for dark mode, dark text for light mode gray button
        color = "white" if page.theme_mode == ft.ThemeMode.DARK else "#1C1C1E"
        btn = ft.ElevatedButton(
            texto,
            on_click=on_click,
            bgcolor=cor_fundo,
            color=color,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(24, 16, 24, 16),
                overlay_color="#339CFF",
                text_style=ft.TextStyle(font_family="Poppins", size=15, weight=ft.FontWeight.W_600),
            ),
        )
        btn.scale = ft.Scale(1.0)
        btn.animate_scale = ft.Animation(200, "easeOut")

        def on_hover(e):
            btn.scale = ft.Scale(1.08 if e.data == "true" else 1.0)
            btn.update()

        btn.on_hover = on_hover
        return btn

    def criar_textfield(label_text, width=320, multiline=False):
        return ft.TextField(
            label=label_text,
            width=min(page.window_width * 0.8, 500),
            border=None,
            border_radius=10,
            bgcolor="#2C2C2E" if page.theme_mode == ft.ThemeMode.DARK else "white",
            color=cor_texto(),
            filled=True,
            multiline=multiline,
            content_padding=ft.Padding(12, 10, 12, 10),
            label_style=ft.TextStyle(
                color="#FFFFFF" if page.theme_mode == ft.ThemeMode.DARK else "#1C1C1E",
                weight=ft.FontWeight.W_500,
                font_family="Poppins",
            ),
            text_style=ft.TextStyle(font_family="Poppins", size=14),
            cursor_color="#007AFF",
        )

    def voltar_ao_menu(e=None):
        # Animação suave de fade para transição
        page.controls.clear()
        container = conteudo_menu()
        container.opacity = 0
        page.add(container)
        container.animate_opacity = ft.Animation(400, "easeOut")
        container.opacity = 1
        page.update()

    def tela_pagamento_avariados(page):
        print("🟢 Função tela_pagamento_avariados() foi chamada corretamente")
        print("🚀 Entrando em tela_pagamento_avariados() - antes dos imports")
        import qrcode
        print("✅ qrcode importado com sucesso!")
        try:
            import qrcode
            from io import BytesIO
            import base64
            print("Carregando tela de pagamento...")
            print("Antes do conectar()")
            page.clean()
            page.title = " Pagamento de Livros Avariados"

            conn = conectar()
            print("Depois do conectar()")
            cursor_pagamento = conn.cursor(dictionary=True)
            try:
                cursor_pagamento.execute("""
                    SELECT la.id, a.nome AS aluno, l.titulo AS livro, la.valor_devido,
                           DATE_FORMAT(e.data_devolucao, '%d/%m/%Y') AS data_devolucao
                    FROM livrosAvariados la
                    JOIN alunos a ON la.id_aluno = a.id_aluno
                    JOIN livros l ON la.id_livro = l.id_livro
                    LEFT JOIN emprestimos e ON e.id_aluno = a.id_aluno AND e.id_livro = l.id_livro
                    WHERE la.pago = 0;
                """)
                pendentes = cursor_pagamento.fetchall()
                # Limpa buffer para evitar Unread result found
                cursor_pagamento.fetchall()
            finally:
                cursor_pagamento.close()
                conn.close()
                print("✅ Conexão fechada e dados carregados.")

            if not pendentes:
                page.add(
                    ft.Text("Nenhum pagamento pendente de livros avariados 🎉", size=16, color=cor_texto()),
                    criar_botao("Voltar ao Menu", voltar_ao_menu)
                )
                return

            # Dropdown de seleção
            opcoes_pagamento = [
                ft.dropdown.Option(
                    text=f"{p['aluno']} - {p['livro']} | R$ {p['valor_devido']:.2f}",
                    key=str(p["id"])
                )
                for p in pendentes
            ]
            dropdown_pagamento = ft.Dropdown(
                label="Selecione o pagamento a registrar",
                options=opcoes_pagamento,
                width=420
            )

            # Containers dinâmicos
            qr_code_img = ft.Image(width=200, height=200)
            detalhes_container = ft.Column([], visible=False)

            # Função para gerar QR Code PIX (nova versão)
            def gerar_qrcode_pix(valor, aluno, livro):
                import qrcode
                from io import BytesIO
                import base64

                valor_str = f"{float(valor):.2f}"
                payload_pix = f"00020126360014BR.GOV.BCB.PIX0114+551199999999520400005303986540{valor_str}5802BR5920Biblioteca Zul6009SaoPaulo62140510PAGAMENTO"
                qr = qrcode.QRCode(version=1, box_size=10, border=3)
                qr.add_data(payload_pix)
                qr.make(fit=True)
                img = qr.make_image(fill_color="black", back_color="white")

                buffer = BytesIO()
                img.save(buffer, format="PNG")
                img_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return img_b64

            # Atualiza visualização ao selecionar um pagamento
            def atualizar_detalhes(e):
                if not dropdown_pagamento.value:
                    detalhes_container.visible = False
                    page.update()
                    return

                # Busca o registro selecionado
                dados = next((p for p in pendentes if str(p["id"]) == dropdown_pagamento.value), None)
                if not dados:
                    return

                qr_data = gerar_qrcode_pix(dados["valor_devido"], dados["aluno"], dados["livro"])
                qr_code_img.src_base64 = qr_data

                detalhes_container.controls = [
                    ft.Text(f"📚 Livro: {dados['livro']}", size=16, color=cor_texto()),
                    ft.Text(f"👤 Aluno: {dados['aluno']}", size=16, color=cor_texto()),
                    ft.Text(f"💸 Valor: R$ {dados['valor_devido']:.2f}", size=16, color="#34C759"),
                    ft.Text(f"📅 Devolvido em: {dados['data_devolucao'] or 'Data não informada'}", size=14, color=cor_texto()),
                    ft.Container(
                        content=qr_code_img,
                        alignment=ft.alignment.center,
                        border_radius=10,
                        padding=10,
                        bgcolor="#F5F5F5" if page.theme_mode == ft.ThemeMode.LIGHT else "#2C2C2E",
                    ),
                    ft.Text(
                        "💡 Escaneie o QR Code acima para efetuar o pagamento via PIX",
                        size=14,
                        color="#8E8E93",
                        italic=True,
                        text_align=ft.TextAlign.CENTER
                    )
                ]
                detalhes_container.visible = True
                page.update()

            dropdown_pagamento.on_change = atualizar_detalhes

            # Registrar pagamento
            def registrar_pagamento(e):
                if not dropdown_pagamento.value:
                    page.snack_bar = ft.SnackBar(ft.Text("Selecione um registro para pagamento!"), open=True)
                    page.update()
                    return
                conn_upd = conectar()
                cursor_update = conn_upd.cursor()
                try:
                    cursor_update.execute("UPDATE livrosAvariados SET pago = 1 WHERE id = %s", (int(dropdown_pagamento.value),))
                    conn_upd.commit()
                    # Limpa buffer após update (não necessário normalmente, mas por segurança)
                    cursor_update.fetchall()
                except Exception as err:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao registrar pagamento: {err}"), open=True)
                    page.update()
                    cursor_update.close()
                    conn_upd.close()
                    return
                cursor_update.close()
                conn_upd.close()

                page.dialog = ft.AlertDialog(title=ft.Text("✅ Pagamento registrado com sucesso!"))
                page.dialog.open = True
                page.update()
                tela_pagamento_avariados(page)

            btn_pagar = criar_botao("Confirmar Pagamento Manualmente", registrar_pagamento, cor_fundo="green")
            btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

            # --- NOVO LAYOUT PAGAMENTO ---
            # Elementos reutilizados
            titulo_pagamento = ft.Text(
                "Pagamento de Livros Avariados",
                size=24,
                weight=ft.FontWeight.BOLD,
                text_align=ft.TextAlign.CENTER,
            )
            # Dropdown já criado: dropdown_pagamento
            # Detalhes já definidos em atualizar_detalhes: detalhes_container
            # Para novo layout, vamos separar as informações
            # Informações do livro, aluno, valor, data e QR code
            info_livro = ft.Text("", size=16, color=cor_texto())
            info_aluno = ft.Text("", size=16, color=cor_texto())
            info_valor = ft.Text("", size=16, color="#34C759")
            info_data = ft.Text("", size=14, color=cor_texto())
            qr_image = ft.Image(width=180, height=180)

            def atualizar_detalhes_novo(e):
                if not dropdown_pagamento.value:
                    info_livro.value = ""
                    info_aluno.value = ""
                    info_valor.value = ""
                    info_data.value = ""
                    qr_image.src_base64 = ""
                    botoes_pagamento.visible = False
                    page.update()
                    return
                dados = next((p for p in pendentes if str(p["id"]) == dropdown_pagamento.value), None)
                if not dados:
                    return
                info_livro.value = f"📚 Livro: {dados['livro']}"
                info_aluno.value = f"👤 Aluno: {dados['aluno']}"
                info_valor.value = f"💸 Valor: R$ {dados['valor_devido']:.2f}"
                info_data.value = f"📅 Devolvido em: {dados['data_devolucao'] or 'Data não informada'}"
                qr_data = gerar_qrcode_pix(dados["valor_devido"], dados["aluno"], dados["livro"])
                qr_image.src_base64 = qr_data
                botoes_pagamento.visible = True
                page.update()

            dropdown_pagamento.on_change = atualizar_detalhes_novo

            botoes_pagamento = ft.Row(
                [
                    criar_botao("Confirmar Pagamento", registrar_pagamento, cor_fundo="green"),
                    criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=10,
                width=350,
                visible=False,
            )

            container_pagamento = ft.Container(
                content=ft.Column(
                    [
                        titulo_pagamento,
                        dropdown_pagamento,
                        info_livro,
                        info_aluno,
                        info_valor,
                        info_data,
                        qr_image,
                        ft.Text(
                            "Escaneie o QR Code acima para efetuar o pagamento via PIX",
                            size=12,
                            italic=True,
                            color="gray",
                            text_align=ft.TextAlign.CENTER,
                        ),
                        botoes_pagamento,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=15,
                ),
                width=450,
                padding=20,
                border_radius=15,
                bgcolor="white",
            )

            # Fundo azul estilo home
            page.bgcolor = "#007BFF"
            page.controls.clear()
            page.add(
                ft.Row(
                    [container_pagamento],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
            page.update()
            print("✅ Tela de pagamento de avariados carregada com sucesso!")
            return
        except ModuleNotFoundError:
            page.dialog = ft.AlertDialog(
                title=ft.Text("Dependência ausente"),
                content=ft.Text("O módulo 'qrcode' não está instalado.\nRode:\n\npip install qrcode[pil] Pillow"),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, "open", False))],
            )
            page.dialog.open = True
            page.update()
            return
        except Exception as err:
            import traceback
            print("Erro inesperado em tela_pagamento_avariados:", err)
            print(traceback.format_exc())
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Ocorreu um erro ao carregar a tela de pagamentos: {err}"),
                open=True
            )
            page.update()


    def registrar_devolucao():
        print("🟢 registrar_devolucao() foi chamada com sucesso")
        conn = conectar()
        # Carrega apenas alunos com empréstimos pendentes
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.id_aluno, a.nome
            FROM alunos a
            JOIN emprestimos e ON e.id_aluno = a.id_aluno
            WHERE e.data_devolucao IS NULL OR e.status = 'Ativo'
        """)
        alunos_com_pendencia = cursor.fetchall()

        aluno_dropdown = ft.Dropdown(
            label="Selecione o Aluno",
            options=[ft.dropdown.Option(a[1]) for a in alunos_com_pendencia] if alunos_com_pendencia else [ft.dropdown.Option("Nenhum aluno com empréstimo pendente")],
            width=min(page.window_width * 0.8, 500),
        )

        # Dropdown de livros inicialmente vazio
        livro_dropdown = ft.Dropdown(
            label="Selecione o Livro",
            options=[ft.dropdown.Option("Selecione um aluno primeiro")],
            width=min(page.window_width * 0.8, 500),
        )

        # Função para carregar livros do aluno selecionado
        def carregar_livros_por_aluno(e):
            aluno_nome = aluno_dropdown.value
            if not aluno_nome or aluno_nome == "Nenhum aluno com empréstimo pendente":
                livro_dropdown.options = [ft.dropdown.Option("Selecione um aluno válido")]
                page.update()
                return

            # Abre uma nova conexão temporária para evitar erro de cursor desconectado
            conn_temp = conectar()
            cursor_temp = conn_temp.cursor()

            cursor_temp.execute("""
                SELECT l.id_livro, l.titulo
                FROM livros l
                JOIN emprestimos e ON e.id_livro = l.id_livro
                JOIN alunos a ON e.id_aluno = a.id_aluno
                WHERE a.nome = %s AND (e.data_devolucao IS NULL OR e.status = 'Ativo')
            """, (aluno_nome,))
            livros_do_aluno = cursor_temp.fetchall()

            # Atualiza o dropdown de livros com base nos resultados
            livro_dropdown.options = (
                [ft.dropdown.Option(l[1]) for l in livros_do_aluno]
                if livros_do_aluno else [ft.dropdown.Option("Nenhum livro pendente")]
            )

            conn_temp.close()
            page.update()

        aluno_dropdown.on_change = carregar_livros_por_aluno

        # Campo de observações
        observacoes_field = criar_textfield("Observações", multiline=True)
        # Switch para livro avariado
        livro_avariado_switch = ft.Switch(label="Livro avariado?", value=False)
        # Campo de valor devido (dano)
        valor_devido_field = criar_textfield("Valor Devido (R$)")
        valor_devido_field.visible = False

        # Função para alternar a visibilidade do campo valor devido
        def alternar_valor_devido(e):
            valor_devido_field.visible = livro_avariado_switch.value
            page.update()
        livro_avariado_switch.on_change = alternar_valor_devido

        def salvar_devolucao(e):
            print("Iniciando processo de devolução")
            aluno_nome = aluno_dropdown.value
            livro_titulo = livro_dropdown.value
            observacoes = observacoes_field.value

            if not aluno_nome or not livro_titulo:
                page.snack_bar = ft.SnackBar(ft.Text("Selecione um aluno e um livro."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                conn = conectar()
                cursor = conn.cursor()

                # Buscar IDs
                cursor.execute("SELECT id_aluno FROM alunos WHERE nome = %s", (aluno_nome,))
                aluno_id = cursor.fetchone()[0]
                cursor.fetchall()  # limpa buffer

                cursor.execute("SELECT id_livro FROM livros WHERE titulo = %s", (livro_titulo,))
                livro_id = cursor.fetchone()[0]
                cursor.fetchall()  # limpa buffer

                # Atualizar empréstimo
                cursor.execute("""
                    UPDATE emprestimos
                    SET data_devolucao = NOW(),
                        status = 'Devolvido',
                        observacoes = %s
                    WHERE id_aluno = %s AND id_livro = %s AND status = 'Ativo'
                """, (observacoes, aluno_id, livro_id))

                # Atualizar disponibilidade e quantidade_ativo do livro
                cursor.execute("""
                    UPDATE livros
                    SET quantidade_ativo = quantidade_ativo + 1,
                        disponibilidade = CASE WHEN quantidade_ativo + 1 > 0 THEN 1 ELSE 0 END
                    WHERE id_livro = %s
                """, (livro_id,))

                # Registrar dano, se o switch estiver ativado e houver valor devido informado
                if livro_avariado_switch.value and valor_devido_field.value:
                    try:
                        valor = float(valor_devido_field.value.replace(",", "."))
                        cursor.execute("""
                            INSERT INTO livrosAvariados (id_aluno, id_livro, valor_devido)
                            VALUES (%s, %s, %s)
                        """, (aluno_id, livro_id, valor))
                    except Exception as err_valor:
                        print(f"Erro ao registrar dano: {err_valor}")

                conn.commit()
                conn.close()

                print("✅ Devolução registrada com sucesso!")
                page.snack_bar = ft.SnackBar(ft.Text("Devolução registrada com sucesso!"))
                page.snack_bar.open = True
                page.update()
                voltar_ao_menu()

            except Exception as e:
                print(f"❌ Erro ao registrar devolução: {e}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao registrar devolução: {e}"))
                page.snack_bar.open = True
                page.update()

        gif = ft.Image(
            src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2UxeHJhamZvdDFocWpqdm43bmowM3poZzdpcXJkejd3bnlvZjF3OSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/AbuQeC846WKOs/giphy.gif",
            width=200,
            height=200,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )

        titulo = ft.Text(
            "Registrar Devolução",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
        )

        btn_salvar = ft.ElevatedButton("Salvar", on_click=salvar_devolucao)
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [
                gif,
                titulo,
                aluno_dropdown,
                livro_dropdown,
                observacoes_field,
                livro_avariado_switch,
                valor_devido_field,
                btn_salvar,
                btn_voltar
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        container = ft.Container(
            content=ft.Column([form], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
        )

        page.controls.clear()
        col = ft.Column(
            [ft.Row([container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def conteudo_menu():
        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNDdpOGgxeDlyMXIzNHRnaHpsdzI3eXVnNHlzOXBlbDFtbWVvaGM5dCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/l0HlMEi55YsfXyzMk/giphy.gif",
            width=180,
            height=180,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )
        titulo = ft.Text(
            "Gerenciamento de Biblioteca",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
            font_family="Poppins",
            italic=True,
        )
        # Grid estilo Zul
        # Define secondary button background and text/icon color based on theme
        secondary_bgcolor = "#3A3A3C" if page.theme_mode == ft.ThemeMode.DARK else "#F0F0F3"
        secondary_color = "white" if page.theme_mode == ft.ThemeMode.DARK else "#1C1C1E"
        botoes = ft.GridView(
            expand=False,
            runs_count=2,
            max_extent=230,
            spacing=20,
            run_spacing=20,
            child_aspect_ratio=1,
            controls=[
                # 1. Cadastrar Empréstimo (blue button)
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.BOOK, size=50, color="white"),
                            ft.Text("Cadastrar Empréstimo", weight=ft.FontWeight.BOLD, color="white", text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor="#007AFF",
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: cadastrar_emprestimo(),
                ),
                # 2. Avaliar Livro
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.STAR, size=50, color=secondary_color),
                            ft.Text("Avaliar Livro", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: avaliar_livro(),
                ),
                # 3. Avaliar Atendimento
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.CHAT, size=50, color=secondary_color),
                            ft.Text("Avaliar Atendimento", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: avaliar_atendimento(),
                ),
                # 4. Cadastrar Livro
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.LIBRARY_ADD, size=50, color=secondary_color),
                            ft.Text("Cadastrar Livro", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: cadastrar_livro(),
                ),
                # 5. Registrar Devolução
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.REPLAY, size=50, color=secondary_color),
                            ft.Text("Registrar Devolução", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: registrar_devolucao(),
                ),
                # 6. Pagamento de Livros Avariados (NOVO BOTÃO)
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.ATTACH_MONEY, size=50, color=secondary_color),
                            ft.Text(" Pagamento de Livros Avariados", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=lambda e: (print("🟢 tela_pagamento_avariados chamada!"), tela_pagamento_avariados(page)),
                ),
                # 7. Gerar Relatório
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(name=ft.Icons.INSIGHTS, size=50, color=secondary_color),
                            ft.Text("Gerar Relatório", weight=ft.FontWeight.BOLD, color=secondary_color, text_align=ft.TextAlign.CENTER),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=5,
                    ),
                    bgcolor=secondary_bgcolor,
                    border_radius=20,
                    padding=25,
                    alignment=ft.alignment.center,
                    on_click=gerar_relatorio,
                ),
            ],
        )
        # Botão de alternância de tema
        def alternar_tema(e):
            if page.theme_mode == ft.ThemeMode.LIGHT:
                page.theme_mode = ft.ThemeMode.DARK
                page.bgcolor = "#121212"
                page.session.set("tema_botao", "#3A3A3C")
                page.session.set("tema_container", "#2C2C2E")
            else:
                page.theme_mode = ft.ThemeMode.LIGHT
                page.bgcolor = "#007AFF"
                page.session.set("tema_botao", "#007AFF")
                page.session.set("tema_container", "white")
            voltar_ao_menu()
            page.update()
        theme_toggle = ft.ElevatedButton(
            text="Alternar tema",
            icon=ft.Icons.BRIGHTNESS_6_OUTLINED,
            on_click=alternar_tema,
            bgcolor=page.session.get("tema_botao") or ("#3A3A3C" if page.theme_mode == ft.ThemeMode.DARK else "#007AFF"),
            color="white",
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                padding=ft.Padding(14, 10, 14, 10),
                overlay_color="#339CFF",
            ),
        )
        container = ft.Container(
            content=ft.Column(
                [gif, titulo, botoes],
                spacing=50,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                scroll=ft.ScrollMode.AUTO,  # adiciona rolagem corretamente
            ),
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
            expand=False,
            shadow=None,
        )
        col = ft.Column(
            [
                ft.Row(
                    [theme_toggle],
                    alignment=ft.MainAxisAlignment.END,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                ft.Row(
                    [container],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                    height=page.window_height,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        return col

    def cadastrar_emprestimo():
        aluno_existe = ft.Switch(label="Aluno já cadastrado?", value=True)

        aluno_dropdown = ft.Dropdown(
            label="Selecione o Aluno",
            options=[ft.dropdown.Option(nome) for nome in (page.session.get("alunos") or alunos)] if alunos else [ft.dropdown.Option("Nenhum aluno cadastrado")],
            width=min(page.window_width * 0.8, 500),
            visible=True
        )
        livro_dropdown = ft.Dropdown(
            label="Selecione o Livro",
            options=[ft.dropdown.Option(titulo) for titulo in livros] if livros else [ft.dropdown.Option("Nenhum livro cadastrado")],
            width=min(page.window_width * 0.8, 500),
            visible=True
        )
        novo_aluno_field = criar_textfield("Nome do Novo Aluno", width=400)
        observacoes_field = criar_textfield("Observações", multiline=True)

        email_input = ft.TextField(label="E-mail do Aluno", width=400)
        curso_input = ft.TextField(label="Curso", width=400)
        email_input.visible = False
        curso_input.visible = False
        novo_aluno_field.visible = False

        def alternar_aluno(e):
            aluno_dropdown.visible = aluno_existe.value
            novo_aluno_field.visible = not aluno_existe.value
            email_input.visible = not aluno_existe.value
            curso_input.visible = not aluno_existe.value
            page.update()

        aluno_existe.on_change = alternar_aluno

        from datetime import datetime
        def salvar_emprestimo(e):
            print("➡️ Iniciando salvar_emprestimo")
            import re
            conn = conectar()
            cursor = conn.cursor()
            # Lógica para aluno
            if aluno_existe.value:
                aluno_nome = aluno_dropdown.value
                print("✅ Aluno existente verificado:", aluno_nome)
                cursor.execute("SELECT id_aluno FROM alunos WHERE nome = %s", (aluno_nome,))
                id_aluno = cursor.fetchone()
                cursor.fetchall()  # limpa buffer antes de novo comando
                if not id_aluno:
                    page.snack_bar = ft.SnackBar(ft.Text("Aluno não encontrado!"))
                    page.snack_bar.open = True
                    page.update()
                    return
                id_aluno = id_aluno[0]
                print("✅ ID do aluno:", id_aluno)
            else:
                aluno_nome = novo_aluno_field.value.strip()
                print("✅ Aluno novo informado:", aluno_nome)
                email_val = email_input.value.strip() if email_input.value else ""
                curso_val = curso_input.value.strip() if curso_input.value else ""
                # Validação de e-mail
                if not re.match(r"[^@]+@[^@]+\.[^@]+", email_val):
                    page.snack_bar = ft.SnackBar(ft.Text("Por favor, insira um e-mail válido."))
                    page.snack_bar.open = True
                    page.update()
                    return
                # Verifica se e-mail já existe
                cursor.execute("SELECT id_aluno FROM alunos WHERE email = %s", (email_val,))
                aluno_existente = cursor.fetchone()
                if aluno_existente:
                    id_aluno = aluno_existente[0]
                else:
                    cursor.execute("""
                        INSERT INTO alunos (nome, email, curso)
                        VALUES (%s, %s, %s)
                    """, (aluno_nome, email_val, curso_val))
                    conn.commit()
                    id_aluno = cursor.lastrowid
                    # Atualiza lista global de alunos
                    cursor.execute("SELECT nome FROM alunos ORDER BY nome;")
                    alunos_atualizados = [row[0] for row in cursor.fetchall()]
                    page.session.set("alunos", alunos_atualizados)
                print("✅ ID do aluno:", id_aluno)

            # Lógica para livro: sempre usa o dropdown e busca o livro existente
            livro_titulo = livro_dropdown.value
            # Remove "(Indisponível no momento)" se houver
            livro_titulo = livro_titulo.replace(" (Indisponível no momento)", "")
            print("✅ Livro selecionado:", livro_titulo)
            cursor.execute("SELECT id_livro FROM livros WHERE titulo = %s", (livro_titulo,))
            livro_existente = cursor.fetchone()
            cursor.fetchall()
            if livro_existente:
                id_livro = livro_existente[0]
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Livro não encontrado!"))
                page.snack_bar.open = True
                page.update()
                conn.close()
                return

            # Verifica se o livro possui estoque ativo
            cursor.execute("SELECT quantidade_ativo FROM livros WHERE id_livro = %s", (id_livro,))
            qtd_row = cursor.fetchone()
            print("✅ Estoque disponível:", qtd_row)
            if not qtd_row or qtd_row[0] <= 0:
                page.snack_bar = ft.SnackBar(ft.Text("❌ Livro indisponível para empréstimo — estoque esgotado."))
                page.snack_bar.open = True
                page.update()
                conn.close()
                return

            # Define data de retirada automaticamente
            data_retirada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.fetchall()  # limpa buffer antes de novo comando
            print("✅ Tentando salvar empréstimo...")
            try:
                cursor.execute("""
                    INSERT INTO emprestimos (id_aluno, id_livro, data_retirada, observacoes, status)
                    VALUES (%s, %s, NOW(), %s, 'Ativo')
                """, (id_aluno, id_livro, observacoes_field.value.strip() or None))
                conn.commit()
                print("✅ Empréstimo salvo com sucesso!")
            except Exception as err:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Erro ao salvar empréstimo: {err}"))
                page.snack_bar.open = True
                page.update()
                conn.rollback()
                conn.close()
                return
            # Atualiza quantidade_ativo e disponibilidade do livro
            cursor.execute("""
                UPDATE livros
                SET quantidade_ativo = GREATEST(quantidade_ativo - 1, 0),
                    disponibilidade = CASE WHEN quantidade_ativo - 1 <= 0 THEN 0 ELSE 1 END
                WHERE id_livro = %s
            """, (id_livro,))
            conn.commit()
            conn.close()
            page.snack_bar = ft.SnackBar(ft.Text("Empréstimo registrado com sucesso!"))
            page.snack_bar.open = True
            page.update()
            voltar_ao_menu()

        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3bDAya2p3eGllNjhta2FuZWhwZmRiMjR5NTc5OG00ZXFqdWZuODEwaiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/toSMxU7Mguxnq/giphy.gif",
            width=200,
            height=200,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )
        titulo = ft.Text(
            "Cadastrar Empréstimo",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
        )

        btn_salvar = criar_botao("Salvar", lambda e: salvar_emprestimo(e))
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [
                gif, titulo,
                aluno_existe, aluno_dropdown, novo_aluno_field, email_input, curso_input,
                livro_dropdown,
                observacoes_field,
                btn_salvar, btn_voltar
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        container = ft.Container(
            content=ft.Column(
                [form],
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
            expand=False,
        )

        page.controls.clear()
        col = ft.Column(
            [
                ft.Row(
                    [container],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                    height=page.window_height,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def cadastrar_livro():
        # Formulário para cadastro de livro
        titulo_field = criar_textfield("Título do Livro")
        autor_field = criar_textfield("Autor")
        categoria_field = criar_textfield("Categoria")
        ano_field = criar_textfield("Ano de Publicação")
        preco_field = criar_textfield("Preço (R$)")
        disponibilidade_switch = ft.Switch(label="Disponível para empréstimo?", value=True)
        livro_existe_switch = ft.Switch(label="Adicionar quantidade a livro já existente?", value=False)

        def salvar_livro(e):
            # Validação
            if not titulo_field.value or not autor_field.value or not categoria_field.value or not ano_field.value or not preco_field.value:
                page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos obrigatórios!"))
                page.snack_bar.open = True
                page.update()
                return
            try:
                ano_int = int(ano_field.value)
                preco_float = float(preco_field.value.replace(",", "."))
            except Exception:
                page.snack_bar = ft.SnackBar(ft.Text("Ano deve ser inteiro e preço deve ser número."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                conn = conectar()
                cursor = conn.cursor()

                if livro_existe_switch.value:
                    # Atualiza quantidade, quantidade_ativo e preço médio de um livro já existente
                    cursor.execute("SELECT id_livro, preco, quantidade, quantidade_ativo FROM livros WHERE titulo = %s", (titulo_field.value.strip(),))
                    livro_existente = cursor.fetchone()
                    if livro_existente:
                        id_livro, preco_atual, qtd_atual, qtd_ativo_atual = livro_existente
                        novo_preco = float(preco_field.value.replace(",", "."))
                        media_preco = ((preco_atual * qtd_atual) + novo_preco) / (qtd_atual + 1)
                        cursor.execute("""
                            UPDATE livros 
                            SET quantidade = quantidade + 1, quantidade_ativo = quantidade_ativo + 1, preco = %s 
                            WHERE id_livro = %s
                        """, (media_preco, id_livro))
                        conn.commit()
                        conn.close()
                        page.snack_bar = ft.SnackBar(ft.Text("📚 Quantidade e quantidade ativa atualizadas e preço médio recalculado!"))
                        page.snack_bar.open = True
                        page.update()
                        return
                    # Se não encontrou, segue para inserção normal

                # Inserção padrão (com quantidade=1, quantidade_ativo=1)
                try:
                    cursor.execute("""
                        INSERT INTO livros (titulo, autor, categoria, ano_publicacao, preco, disponibilidade, quantidade, quantidade_ativo)
                        VALUES (%s, %s, %s, %s, %s, %s, 1, 1)
                    """, (
                        titulo_field.value.strip(),
                        autor_field.value.strip(),
                        categoria_field.value.strip(),
                        ano_int,
                        preco_float,
                        1 if disponibilidade_switch.value else 0
                    ))
                except Exception as err_cat:
                    # Fallback: se a tabela tiver 'genero' em vez de 'categoria'
                    cursor.execute("""
                        INSERT INTO livros (titulo, autor, genero, ano_publicacao, preco, disponibilidade, quantidade, quantidade_ativo)
                        VALUES (%s, %s, %s, %s, %s, %s, 1, 1)
                    """, (
                        titulo_field.value.strip(),
                        autor_field.value.strip(),
                        categoria_field.value.strip(),
                        ano_int,
                        preco_float,
                        1 if disponibilidade_switch.value else 0
                    ))

                conn.commit()
                conn.close()

                page.snack_bar = ft.SnackBar(ft.Text("✅ Livro cadastrado com sucesso!"))
                page.snack_bar.open = True
                page.update()

                # Limpa os campos
                titulo_field.value = ""
                autor_field.value = ""
                categoria_field.value = ""
                ano_field.value = ""
                preco_field.value = ""
                disponibilidade_switch.value = True
                page.update()

            except Exception as ex:
                page.snack_bar = ft.SnackBar(ft.Text(f"❌ Erro ao salvar livro: {ex}"))
                page.snack_bar.open = True
                page.update()

        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExcDhyZjB1Z2ZybXYzZmV4bmIxejU4Ymxuc2V4M2lvZTkzYjJ1bms0ZiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/1wmcpshIDQXQbqDSuZ/giphy.gif",
            width=200, height=200, border_radius=20, fit=ft.ImageFit.COVER,
        )
        titulo = ft.Text("Cadastrar Livro", size=26, weight=ft.FontWeight.BOLD, color=cor_texto(),
                         text_align=ft.TextAlign.CENTER)
        btn_salvar = criar_botao("Salvar", salvar_livro)
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [
                gif, titulo,
                livro_existe_switch,
                titulo_field, autor_field, categoria_field, ano_field, preco_field, disponibilidade_switch,
                btn_salvar, btn_voltar
            ],
            spacing=20, alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        container = ft.Container(
            content=ft.Column([form], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#FFFFFF" if page.theme_mode == ft.ThemeMode.LIGHT else "#2C2C2E",
            border_radius=20, padding=40, alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
        )

        page.controls.clear()
        col = ft.Column(
            [ft.Row([container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True)],
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def avaliar_livro():
        conn = conectar()
        cursor = conn.cursor(dictionary=True)

        # Carrega apenas alunos que ainda têm pelo menos um livro não avaliado
        cursor.execute("""
            SELECT DISTINCT a.id_aluno, a.nome
            FROM alunos a
            JOIN emprestimos e ON e.id_aluno = a.id_aluno
            WHERE EXISTS (
                SELECT 1 FROM emprestimos e2
                WHERE e2.id_aluno = a.id_aluno
                AND NOT EXISTS (
                    SELECT 1 FROM avaliacoes av
                    WHERE av.id_aluno = a.id_aluno
                    AND av.id_livro = e2.id_livro
                )
            )
        """)
        alunos_com_emprestimo = cursor.fetchall()
        conn.close()

        aluno_dropdown = ft.Dropdown(
            label="Selecione o Aluno",
            options=[ft.dropdown.Option(a["nome"]) for a in alunos_com_emprestimo] if alunos_com_emprestimo else [ft.dropdown.Option("Nenhum aluno com empréstimos")],
            width=min(page.window_width * 0.8, 500),
            on_change=lambda e: carregar_livros_por_aluno(e),
        )

        livro_dropdown = ft.Dropdown(
            label="Selecione o Livro",
            options=[ft.dropdown.Option("Selecione um aluno primeiro")],
            width=min(page.window_width * 0.8, 500),
            menu_height=250
        )

        avaliacao = criar_textfield("Nota (0-5)")
        comentarios = criar_textfield("Comentários", multiline=True)

        def carregar_livros_por_aluno(e):
            aluno_nome = aluno_dropdown.value
            if not aluno_nome:
                livro_dropdown.options = [ft.dropdown.Option("Selecione um aluno válido")]
                page.update()
                return

            conn_temp = conectar()
            cursor_temp = conn_temp.cursor(dictionary=True)

            cursor_temp.execute("""
                SELECT DISTINCT l.id_livro, l.titulo
                FROM emprestimos e
                JOIN livros l ON e.id_livro = l.id_livro
                JOIN alunos a ON e.id_aluno = a.id_aluno
                WHERE a.nome = %s
                AND e.id_emprestimo NOT IN (
                    SELECT id_emprestimo FROM avaliacoes
                    WHERE id_aluno = a.id_aluno AND id_livro = l.id_livro
                )
            """, (aluno_nome,))
            livros = cursor_temp.fetchall()
            conn_temp.close()

            livro_dropdown.options = [ft.dropdown.Option(l["titulo"]) for l in livros] if livros else [ft.dropdown.Option("Nenhum livro disponível para avaliar")]
            page.update()

        def salvar_avaliacao(e):
            if not aluno_dropdown.value or not livro_dropdown.value or not avaliacao.value:
                page.snack_bar = ft.SnackBar(ft.Text("Por favor, preencha todos os campos obrigatórios."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                nota_txt = avaliacao.value.replace(',', '.').strip()
                nota_float = float(nota_txt)
                if nota_float < 0 or nota_float > 5:
                    raise ValueError
            except:
                page.snack_bar = ft.SnackBar(ft.Text("Nota deve ser um número entre 0 e 5."))
                page.snack_bar.open = True
                page.update()
                return

            conn2 = conectar()
            cursor2 = conn2.cursor(dictionary=True)

            cursor2.execute("SELECT id_aluno FROM alunos WHERE nome = %s", (aluno_dropdown.value,))
            id_aluno_row = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer
            if not id_aluno_row:
                page.snack_bar = ft.SnackBar(ft.Text("Aluno não encontrado."))
                page.snack_bar.open = True
                page.update()
                conn2.close()
                return
            id_aluno = id_aluno_row["id_aluno"]

            cursor2.execute("SELECT id_livro FROM livros WHERE titulo = %s", (livro_dropdown.value,))
            id_livro_row = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer
            if not id_livro_row:
                page.snack_bar = ft.SnackBar(ft.Text("Livro não encontrado."))
                page.snack_bar.open = True
                page.update()
                conn2.close()
                return
            id_livro = id_livro_row["id_livro"]

            cursor2.execute("""
                SELECT COUNT(*) AS total FROM avaliacoes
                WHERE id_aluno = %s AND id_livro = %s
            """, (id_aluno, id_livro))
            ja_avaliou_row = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer
            ja_avaliou = ja_avaliou_row and ja_avaliou_row["total"] > 0

            if ja_avaliou:
                page.snack_bar = ft.SnackBar(ft.Text("Esse livro já foi avaliado por este aluno."))
                page.snack_bar.open = True
                page.update()
                conn2.close()
                return

            cursor2.execute("""
                INSERT INTO avaliacoes (id_aluno, id_livro, nota, comentario)
                VALUES (%s, %s, %s, %s)
            """, (id_aluno, id_livro, nota_float, comentarios.value.strip() if comentarios.value else None))
            conn2.commit()
            conn2.close()

            dialog.title = ft.Text("Sucesso")
            dialog.content = ft.Text("Avaliação cadastrada com sucesso!")
            dialog.open = True
            page.dialog = dialog
            page.update()
            voltar_ao_menu()

        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3d2tqamlqeXlqd2dhZWMxNHl1dTB4M2cwc21zMmhla3k0bHhjY3ZrNiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/oKVo9lyuryCqNMVN2t/giphy.gif",
            width=200,
            height=200,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )
        titulo = ft.Text(
            "Avaliar Livro",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
        )

        btn_salvar = criar_botao("Salvar", salvar_avaliacao)
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [gif, titulo, aluno_dropdown, livro_dropdown, avaliacao, comentarios, btn_salvar, btn_voltar],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        container = ft.Container(
            content=form,
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
            expand=False,
        )

        page.controls.clear()
        col = ft.Column(
            [
                ft.Row(
                    [container],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                    height=page.window_height,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def avaliar_atendimento():
        conn = conectar()
        cursor = conn.cursor(dictionary=True)
        # Garante a criação da tabela
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS avaliacoes_atendimento (
                id INT AUTO_INCREMENT PRIMARY KEY,
                id_aluno INT,
                id_emprestimo INT,
                nota INT,
                comentario TEXT,
                data_avaliacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (id_aluno) REFERENCES alunos(id_aluno),
                FOREIGN KEY (id_emprestimo) REFERENCES emprestimos(id_emprestimo)
            )
        """)
        conn.commit()
        # Busca todos os alunos com empréstimos ativos
        cursor.execute("""
            SELECT DISTINCT a.nome
            FROM alunos a
            JOIN emprestimos e ON e.id_aluno = a.id_aluno
            WHERE e.data_devolucao IS NULL OR e.status = 'Ativo'
        """)
        alunos = cursor.fetchall()
        conn.close()

        usuario_dropdown = ft.Dropdown(
            label="Nome do Usuário",
            options=[ft.dropdown.Option(a["nome"]) for a in alunos] if alunos else [ft.dropdown.Option("Nenhum aluno com empréstimo ativo")],
            width=min(page.window_width * 0.8, 500),
            menu_height=250
        )
        nota = criar_textfield("Nota (0-10)")
        comentario = criar_textfield("Comentários", multiline=True)

        def salvar_atendimento(e):
            if not usuario_dropdown.value or not nota.value:
                page.snack_bar = ft.SnackBar(ft.Text("Por favor, preencha os campos obrigatórios."))
                page.snack_bar.open = True
                page.update()
                return
            try:
                nota_int = int(nota.value)
                if nota_int < 0 or nota_int > 10:
                    raise ValueError
            except:
                page.snack_bar = ft.SnackBar(ft.Text("Nota deve ser um número inteiro entre 0 e 10."))
                page.snack_bar.open = True
                page.update()
                return

            conn2 = conectar()
            cursor2 = conn2.cursor(dictionary=True)

            # Busca aluno
            cursor2.execute("SELECT id_aluno FROM alunos WHERE nome = %s", (usuario_dropdown.value.strip(),))
            aluno_row = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer
            if not aluno_row:
                page.snack_bar = ft.SnackBar(ft.Text("Usuário não encontrado."))
                page.snack_bar.open = True
                page.update()
                conn2.close()
                return
            id_aluno = aluno_row["id_aluno"]

            # Busca o último empréstimo
            cursor2.execute("""
                SELECT id_emprestimo 
                FROM emprestimos 
                WHERE id_aluno = %s 
                ORDER BY data_retirada DESC 
                LIMIT 1
            """, (id_aluno,))
            emp_row = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer
            if not emp_row:
                page.snack_bar = ft.SnackBar(ft.Text("Nenhum empréstimo encontrado para este usuário."))
                page.snack_bar.open = True
                page.update()
                conn2.close()
                return
            id_emprestimo = emp_row["id_emprestimo"]

            # Verifica se já existe avaliação
            cursor2.execute("""
                SELECT COUNT(*) AS total 
                FROM avaliacoes_atendimento 
                WHERE id_aluno = %s AND id_emprestimo = %s
            """, (id_aluno, id_emprestimo))
            ja_avaliou = cursor2.fetchone()
            cursor2.fetchall()  # limpa buffer

            if ja_avaliou and ja_avaliou["total"] > 0:
                cursor2.execute("""
                    UPDATE avaliacoes_atendimento
                    SET nota = %s, comentario = %s, data_avaliacao = CURRENT_TIMESTAMP
                    WHERE id_aluno = %s AND id_emprestimo = %s
                """, (nota_int, comentario.value.strip() if comentario.value else None, id_aluno, id_emprestimo))
                msg = "Avaliação atualizada com sucesso!"
            else:
                cursor2.execute("""
                    INSERT INTO avaliacoes_atendimento (id_aluno, id_emprestimo, nota, comentario)
                    VALUES (%s, %s, %s, %s)
                """, (id_aluno, id_emprestimo, nota_int, comentario.value.strip() if comentario.value else None))
                msg = "Avaliação salva com sucesso!"

            conn2.commit()
            conn2.close()

            page.dialog = ft.AlertDialog(
                title=ft.Text("Sucesso"),
                content=ft.Text(msg),
                actions=[ft.TextButton("OK", on_click=lambda e: setattr(page.dialog, "open", False))]
            )
            page.dialog.open = True
            page.update()
            voltar_ao_menu()

        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPWVjZjA1ZTQ3aHh4MXl3eTh0NWh5NW0zamtjNDU3NDBmcnlobG9nMXZpd2R1eGQ1ZiZlcD12MV9naWZzX3NlYXJjaCZjdD1n/Ue4dqNqYHBepmsqkbN/giphy.gif",
            width=200, height=200, border_radius=20, fit=ft.ImageFit.COVER,
        )
        titulo = ft.Text("Avaliar Atendimento", size=26, weight=ft.FontWeight.BOLD, color=cor_texto(), text_align=ft.TextAlign.CENTER)
        btn_salvar = criar_botao("Salvar", salvar_atendimento)
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [gif, titulo, usuario_dropdown, nota, comentario, btn_salvar, btn_voltar],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        container = ft.Container(
            content=form,
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
            expand=False,
        )
        page.controls.clear()
        col = ft.Column(
            [ft.Row([container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def gerar_relatorio(e=None):
        # GIF centralizado no topo
        gif = ft.Image(
            src="https://media.giphy.com/media/v1.Y2lkPTc5MGI3NjExNDdpOGgxeDlyMXIzNHRnaHpsdzI3eXVnNHlzOXBlbDFtbWVvaGM5dCZlcD12MV9naWZzX3NlYXJjaCZjdD1n/l0HlMEi55YsfXyzMk/giphy.gif",
            width=180,
            height=180,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )

        titulo = ft.Text(
            "Relatório Completo",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
            font_family="Poppins",
            italic=True,
        )

        def criar_card(titulo_texto, conteudo_widgets):
            cabecalho = ft.Text(
                titulo_texto,
                size=18,
                weight=ft.FontWeight.BOLD,
                color=cor_texto(),
                font_family="Poppins",
            )
            # Definir cor de fundo levemente acinzentada (claro) ou mais escura (escuro)
            if page.theme_mode == ft.ThemeMode.DARK:
                card_bgcolor = "#232325"
            else:
                card_bgcolor = "#F4F4F7"
            card_container = ft.Container(
                content=ft.Column(conteudo_widgets, spacing=8),
                bgcolor=card_bgcolor,
                padding=20,
                border_radius=15,
                width=min(page.window_width * 0.84, 500),
                expand=False,
                margin=ft.Margin(0, 10, 0, 10),
                shadow=ft.BoxShadow(blur_radius=8, color="#00000020", offset=ft.Offset(0, 2)),
            )
            # Retorna o cabeçalho acima do container, alinhando à esquerda
            return ft.Column([cabecalho, card_container], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.START)

        # Empréstimos
        emprestimos_widgets_ativos = []
        emprestimos_widgets_concluidos = []

        # Consulta atualizada do banco
        conn_emp = conectar()
        cursor_emp = conn_emp.cursor(dictionary=True)
        cursor_emp.execute("""
            SELECT l.titulo AS livro, a.nome AS aluno,
                   DATE_FORMAT(e.data_retirada, '%d/%m/%Y') AS data_retirada,
                   DATE_FORMAT(e.data_devolucao, '%d/%m/%Y') AS data_devolucao
            FROM emprestimos e
            JOIN livros l ON e.id_livro = l.id_livro
            JOIN alunos a ON e.id_aluno = a.id_aluno
            ORDER BY e.data_retirada DESC;
        """)
        emprestimos_bd = cursor_emp.fetchall()
        conn_emp.close()

        for emp in emprestimos_bd:
            if emp["data_devolucao"]:
                # Livro já devolvido
                emprestimos_widgets_concluidos.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(name=ft.Icons.BOOK_OUTLINED, color="#4CD964", size=20),
                            ft.Column([
                                ft.Text(f"📗 {emp['livro']}", size=15, weight=ft.FontWeight.BOLD, color=cor_texto()),
                                ft.Text(f"👤 {emp['aluno']}", size=13, color=cor_texto()),
                                ft.Text(f"📅 Retirada: {emp['data_retirada']}  |  ✅ Devolução: {emp['data_devolucao']}", size=12, color="#4CD964")
                            ], spacing=2)
                        ]),
                        padding=10,
                        bgcolor="#E8F5E9" if page.theme_mode == ft.ThemeMode.LIGHT else "#1E2F1E",
                        border=ft.border.all(1, "#34C759"),
                        border_radius=10,
                        margin=ft.Margin(0, 4, 0, 4),
                    )
                )
            else:
                # Livro ainda emprestado
                emprestimos_widgets_ativos.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(name=ft.Icons.BOOK_OUTLINED, color="#FF9500", size=20),
                            ft.Column([
                                ft.Text(f"📘 {emp['livro']}", size=15, weight=ft.FontWeight.BOLD, color=cor_texto()),
                                ft.Text(f"👤 {emp['aluno']}", size=13, color=cor_texto()),
                                ft.Text(f"📅 Retirada: {emp['data_retirada']}", size=12, color="#FF9500")
                            ], spacing=2)
                        ]),
                        padding=10,
                        bgcolor="#FFF6E5" if page.theme_mode == ft.ThemeMode.LIGHT else "#2E2414",
                        border=ft.border.all(1, "#FF9500"),
                        border_radius=10,
                        margin=ft.Margin(0, 4, 0, 4),
                    )
                )

        # Cards separados
        card_emprestimos_ativos = criar_card("📚 Empréstimos em Andamento", emprestimos_widgets_ativos if emprestimos_widgets_ativos else [ft.Text("Nenhum livro em posse de alunos.", size=14, color=cor_texto())])
        card_emprestimos_concluidos = criar_card("✅ Empréstimos Concluídos", emprestimos_widgets_concluidos if emprestimos_widgets_concluidos else [ft.Text("Nenhuma devolução registrada.", size=14, color=cor_texto())])

        # Avaliações de Livros
        avaliacoes_livros_widgets = []
        if avaliacoesLivros:
            for i, av in enumerate(avaliacoesLivros, start=1):
                avaliacoes_livros_widgets.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(
                                name=ft.Icons.STAR_OUTLINE,
                                color="#FFCC00" if page.theme_mode == ft.ThemeMode.LIGHT else "#0A84FF",
                                size=20,
                            ),
                            ft.Column([
                                ft.Text(f"📖 {av['livro']} ({av['nota']}/5)", size=15, weight=ft.FontWeight.BOLD, color=cor_texto()),
                                ft.Text(f"👤 {av['usuario']}", size=13, color=cor_texto()),
                                ft.Text(f"💬 {av['comentario']}", size=12, color=cor_texto(), italic=True),
                            ], spacing=2)
                        ]),
                        padding=10,
                        bgcolor="#1E1E1F" if page.theme_mode == ft.ThemeMode.DARK else "#FFFDD0",
                        border=ft.border.all(1, "#0A84FF" if page.theme_mode == ft.ThemeMode.DARK else "#007AFF"),
                        border_radius=10,
                        margin=ft.Margin(0, 4, 0, 4),
                    )
                )
        else:
            avaliacoes_livros_widgets.append(
                ft.Text("Nenhuma avaliação de livro registrada.", size=14, color=cor_texto(), font_family="Poppins")
            )

        # Avaliações de Atendimento
        avaliacoes_atendimento_widgets = []
        if avaliacoesBiblioteca:
            for i, av in enumerate(avaliacoesBiblioteca, start=1):
                avaliacoes_atendimento_widgets.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(name=ft.Icons.SUPPORT_AGENT, color="#0A84FF", size=20),
                            ft.Column([
                                ft.Text(f"⭐ {av['nota']}/10", size=15, weight=ft.FontWeight.BOLD, color=cor_texto()),
                                ft.Text(f"💬 {av['comentario']}", size=12, color=cor_texto(), italic=True),
                            ], spacing=2)
                        ]),
                        padding=10,
                        bgcolor="#1E1E1F" if page.theme_mode == ft.ThemeMode.DARK else "#FFFDD0",
                        border=ft.border.all(1, "#0A84FF" if page.theme_mode == ft.ThemeMode.DARK else "#007AFF"),
                        border_radius=10,
                        margin=ft.Margin(0, 4, 0, 4),
                    )
                )
        else:
            avaliacoes_atendimento_widgets.append(
                ft.Text("Nenhuma avaliação de atendimento registrada.", size=14, color=cor_texto(), font_family="Poppins")
            )

        card_avaliacoes_livros = criar_card("Avaliações de Livros", avaliacoes_livros_widgets)
        card_avaliacoes_atendimento = criar_card("Avaliações de Atendimento", avaliacoes_atendimento_widgets)

        # Livros Avariados
        conn_danos = conectar()
        cursor_danos = conn_danos.cursor(dictionary=True)
        cursor_danos.execute("""
            SELECT la.id_aluno, a.nome AS aluno, l.titulo AS livro, la.valor_devido, la.pago
            FROM livrosAvariados la
            JOIN alunos a ON la.id_aluno = a.id_aluno
            JOIN livros l ON la.id_livro = l.id_livro
            ORDER BY la.pago ASC, a.nome;
        """)
        danos = cursor_danos.fetchall()
        conn_danos.close()

        danos_pendentes_widgets = []
        danos_pagos_widgets = []

        for d in danos:
            card_cor = "#FF3B30" if not d["pago"] else "#34C759"
            bg_cor = "#FFECEC" if not d["pago"] else "#E6F9EA"
            status = "❌ Pendente" if not d["pago"] else "✅ Pago"
            container = ft.Container(
                content=ft.Row([
                    ft.Icon(name=ft.Icons.REPORT_PROBLEM, color=card_cor, size=20),
                    ft.Column([
                        ft.Text(f"📘 {d['livro']}", size=15, weight=ft.FontWeight.BOLD, color=cor_texto()),
                        ft.Text(f"👤 {d['aluno']}", size=13, color=cor_texto()),
                        ft.Text(f"💸 Valor: R$ {d['valor_devido']:.2f} | {status}", size=12, color=card_cor)
                    ], spacing=2)
                ]),
                padding=10,
                bgcolor=bg_cor if page.theme_mode == ft.ThemeMode.LIGHT else "#2E1F1F",
                border=ft.border.all(1, card_cor),
                border_radius=10,
                margin=ft.Margin(0, 4, 0, 4),
            )
            if d["pago"]:
                danos_pagos_widgets.append(container)
            else:
                danos_pendentes_widgets.append(container)

        card_danos_pendentes = criar_card(
            "💥 Livros Avariados Pendentes",
            danos_pendentes_widgets if danos_pendentes_widgets else [
                ft.Text("Nenhum livro avariado pendente.", size=14, color=cor_texto())
            ]
        )

        card_danos_pagos = criar_card(
            "💰 Livros Avariados Pagos",
            danos_pagos_widgets if danos_pagos_widgets else [
                ft.Text("Nenhum pagamento de dano registrado.", size=14, color=cor_texto())
            ]
        )

        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        # Divider para separação visual
        divider = ft.Divider(height=10, thickness=1, color="#CCCCCC40")

        # Conteúdo centralizado estilo cartão, com divisores suaves entre cards principais
        conteudo = ft.Column(
            [
                gif,
                titulo,
                card_emprestimos_ativos,
                card_emprestimos_concluidos,
                divider,
                card_danos_pendentes,
                card_danos_pagos,
                card_avaliacoes_livros,
                divider,
                card_avaliacoes_atendimento,
                btn_voltar,
            ],
            spacing=30,  # espaço maior acima do botão
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            width=min(page.window_width * 0.9, 500),
            expand=False,
        )
        # Centralizar título
        conteudo.spacing = 25
        conteudo.controls[1].text_align = ft.TextAlign.CENTER

        container = ft.Container(
            content=ft.Column(
                [conteudo],
                scroll=ft.ScrollMode.AUTO,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.98, 540),
            expand=False,
            shadow=None,
        )

        # Animação suave de fade e centralização vertical/horizontal
        print("Gerando relatório...")
        page.controls.clear()
        page.update()
        col = ft.Column(
            [
                ft.Row(
                    [container],
                    alignment=ft.MainAxisAlignment.CENTER,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    expand=True,
                    height=page.window_height,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    def registrar_devolucao():
        print("🟢 Função registrar_devolucao foi chamada!")
        conn = conectar()
        # Carrega apenas alunos com empréstimos pendentes
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.id_aluno, a.nome
            FROM alunos a
            JOIN emprestimos e ON e.id_aluno = a.id_aluno
            WHERE e.data_devolucao IS NULL OR e.status = 'Ativo'
        """)
        alunos_com_pendencia = cursor.fetchall()

        aluno_dropdown = ft.Dropdown(
            label="Selecione o Aluno",
            options=[ft.dropdown.Option(a[1]) for a in alunos_com_pendencia] if alunos_com_pendencia else [ft.dropdown.Option("Nenhum aluno com empréstimo pendente")],
            width=min(page.window_width * 0.8, 500),
        )

        # Dropdown de livros inicialmente vazio
        livro_dropdown = ft.Dropdown(
            label="Selecione o Livro",
            options=[ft.dropdown.Option("Selecione um aluno primeiro")],
            width=min(page.window_width * 0.8, 500),
        )

        # Função para carregar livros do aluno selecionado
        def carregar_livros_por_aluno(e):
            aluno_nome = aluno_dropdown.value
            if not aluno_nome or aluno_nome == "Nenhum aluno com empréstimo pendente":
                livro_dropdown.options = [ft.dropdown.Option("Selecione um aluno válido")]
                page.update()
                return

            # Abre uma nova conexão temporária para evitar erro de cursor desconectado
            conn_temp = conectar()
            cursor_temp = conn_temp.cursor()

            cursor_temp.execute("""
                SELECT l.id_livro, l.titulo
                FROM livros l
                JOIN emprestimos e ON e.id_livro = l.id_livro
                JOIN alunos a ON e.id_aluno = a.id_aluno
                WHERE a.nome = %s AND (e.data_devolucao IS NULL OR e.status = 'Ativo')
            """, (aluno_nome,))
            livros_do_aluno = cursor_temp.fetchall()

            # Atualiza o dropdown de livros com base nos resultados
            livro_dropdown.options = (
                [ft.dropdown.Option(l[1]) for l in livros_do_aluno]
                if livros_do_aluno else [ft.dropdown.Option("Nenhum livro pendente")]
            )

            conn_temp.close()
            page.update()

        aluno_dropdown.on_change = carregar_livros_por_aluno

        # Campo de observações
        observacoes_field = criar_textfield("Observações", multiline=True)
        # Switch para livro avariado
        livro_avariado_switch = ft.Switch(label="Livro avariado?", value=False)
        # Campo de valor devido (dano)
        valor_devido_field = criar_textfield("Valor Devido (R$)")
        valor_devido_field.visible = False

        # Função para alternar a visibilidade do campo valor devido
        def alternar_valor_devido(e):
            valor_devido_field.visible = livro_avariado_switch.value
            page.update()
        livro_avariado_switch.on_change = alternar_valor_devido

        def salvar_devolucao(e):
            print("Iniciando processo de devolução")
            aluno_nome = aluno_dropdown.value
            livro_titulo = livro_dropdown.value
            observacoes = observacoes_field.value

            if not aluno_nome or not livro_titulo:
                page.snack_bar = ft.SnackBar(ft.Text("Selecione um aluno e um livro."))
                page.snack_bar.open = True
                page.update()
                return

            try:
                conn = conectar()
                cursor = conn.cursor()

                # Buscar IDs
                cursor.execute("SELECT id_aluno FROM alunos WHERE nome = %s", (aluno_nome,))
                aluno_id = cursor.fetchone()[0]
                cursor.fetchall()  # limpa buffer

                cursor.execute("SELECT id_livro FROM livros WHERE titulo = %s", (livro_titulo,))
                livro_id = cursor.fetchone()[0]
                cursor.fetchall()  # limpa buffer

                # Atualizar empréstimo
                cursor.execute("""
                    UPDATE emprestimos
                    SET data_devolucao = NOW(),
                        status = 'Devolvido',
                        observacoes = %s
                    WHERE id_aluno = %s AND id_livro = %s AND status = 'Ativo'
                """, (observacoes, aluno_id, livro_id))

                # Atualizar disponibilidade e quantidade_ativo do livro
                cursor.execute("""
                    UPDATE livros
                    SET quantidade_ativo = quantidade_ativo + 1,
                        disponibilidade = CASE WHEN quantidade_ativo + 1 > 0 THEN 1 ELSE 0 END
                    WHERE id_livro = %s
                """, (livro_id,))

                # Registrar dano, se o switch estiver ativado e houver valor devido informado
                if livro_avariado_switch.value and valor_devido_field.value:
                    try:
                        valor = float(valor_devido_field.value.replace(",", "."))
                        cursor.execute("""
                            INSERT INTO livrosAvariados (id_aluno, id_livro, valor_devido)
                            VALUES (%s, %s, %s)
                        """, (aluno_id, livro_id, valor))
                    except Exception as err_valor:
                        print(f"Erro ao registrar dano: {err_valor}")

                conn.commit()
                conn.close()

                print("✅ Devolução registrada com sucesso!")
                page.snack_bar = ft.SnackBar(ft.Text("Devolução registrada com sucesso!"))
                page.snack_bar.open = True
                page.update()
                voltar_ao_menu()

            except Exception as e:
                print(f"❌ Erro ao registrar devolução: {e}")
                page.snack_bar = ft.SnackBar(ft.Text(f"Erro ao registrar devolução: {e}"))
                page.snack_bar.open = True
                page.update()

        gif = ft.Image(
            src="https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExc2UxeHJhamZvdDFocWpqdm43bmowM3poZzdpcXJkejd3bnlvZjF3OSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/AbuQeC846WKOs/giphy.gif",
            width=200,
            height=200,
            border_radius=20,
            fit=ft.ImageFit.COVER,
        )

        titulo = ft.Text(
            "Registrar Devolução",
            size=26,
            weight=ft.FontWeight.BOLD,
            color=cor_texto(),
            text_align=ft.TextAlign.CENTER,
        )

        btn_salvar = ft.ElevatedButton("Salvar", on_click=salvar_devolucao)
        btn_voltar = criar_botao("Voltar ao Menu", voltar_ao_menu, cor_fundo="red")

        form = ft.Column(
            [
                gif,
                titulo,
                aluno_dropdown,
                livro_dropdown,
                observacoes_field,
                livro_avariado_switch,
                valor_devido_field,
                btn_salvar,
                btn_voltar
            ],
            spacing=20,
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

        container = ft.Container(
            content=ft.Column([form], scroll=ft.ScrollMode.AUTO, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=page.session.get("tema_container") or "white",
            border_radius=20,
            padding=40,
            alignment=ft.alignment.center,
            width=min(page.window_width * 0.8, 500),
        )

        page.controls.clear()
        col = ft.Column(
            [ft.Row([container], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True)],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        col.opacity = 0
        page.add(col)
        col.animate_opacity = ft.Animation(400, "easeOut")
        col.opacity = 1
        page.update()

    menu = conteudo_menu()
    page.add(menu)
    page.update()

if __name__ == "__main__":
    ft.app(target=main)