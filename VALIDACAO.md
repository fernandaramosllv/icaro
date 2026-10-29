# Validação técnica

Ambiente principal: Windows 11 x64 com CPython 3.12 x64.

## Testes automatizados

A suíte possui **46 testes com unittest e unittest.mock**. A última execução anterior à preparação para publicação terminou com sucesso. Os testes não abrem aplicativos reais, não navegam na web, não acessam o serviço de síntese e não dependem de microfone.

| Área | Cenários |
| --- | --- |
| Interpretação | Português, acentos, maiúsculas, argumentos e frases desconhecidas |
| Configuração | Padrões independentes, JSON inválido, tipos, caminhos e conflitos de nomes |
| Navegação | HTTP/HTTPS, domínio, IP, host/porta inválidos e recusa de credenciais |
| Pesquisa | Codificação e recuperação dos termos com caracteres especiais |
| Aplicativos | Caminhos com espaços, ausência de executável e erro de criação de processo |
| CLI | Texto, fim da entrada, Ctrl+C, seleção de dispositivo, mute e erros |
| Captura | Fechamento em saída e falha, modelo antigo, perda de áudio e retomada |
| Síntese | Voz masculina neural, respostas repetidas, áudio vazio, timeout, tamanho e erro de saída |

Execução:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Em ambientes com a pasta temporária padrão bloqueada:

```powershell
New-Item -ItemType Directory -Force work/temp | Out-Null
.\.venv\Scripts\python.exe -c "import tempfile,unittest;tempfile.tempdir='work/temp';r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('tests'));raise SystemExit(not r.wasSuccessful())"
```

## Validação manual observada

- Modo texto executado com ajuda/sugestões, comando inválido e encerramento.
- Dependências instaladas na venv Python 3.12; `pip check` sem conflitos declarados.
- Modelo português `vosk-model-small-pt-0.3` e reconhecedor Vosk carregados realmente.
- Funcionamento do modo voz confirmado pelo usuário no computador de uso.
- Síntese neural Antônio testada com frase fixa: 38.448 bytes de MP3 recebidos e reprodução concluída sem erro.
- ZIP conferido por lista de arquivos, conteúdo e CRC nas entregas locais; não é enviado ao Git.

## Limites da evidência

- A suíte simula as integrações e não valida drivers ou disponibilidade de serviços.
- Não há medição de cobertura, taxa de erro de transcrição ou latência.
- Não foi feito um teste manual documentado de cada aplicativo em todas as variantes de instalação.
- Qualidade percebida da voz depende de avaliação auditiva e das condições de reprodução.
- Mudanças do serviço online, permissões e diferenças de hardware podem causar falhas.
- Outras versões do Python e arquiteturas não são a base da validação publicada.

O workflow de GitHub Actions verifica a suíte automatizada, não os testes manuais de hardware.
