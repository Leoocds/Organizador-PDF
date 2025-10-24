Este projeto é uma ferramenta gráfica para compactação e organização de arquivos PDF. Ele permite ao usuário selecionar uma pasta com PDFs, definir um tamanho máximo por arquivo (em MB) e processar automaticamente:

Compacta PDFs maiores que o limite definido.

Divide PDFs que não cabem no tamanho máximo em partes menores, salvando cada parte separadamente.

Mantém PDFs já dentro do limite sem alterações.

Exibe logs detalhados do processamento na própria interface.

Tecnologias utilizadas:

Python

Tkinter (interface gráfica)

PyPDF2 (manipulação de PDFs)

Ghostscript (compactação de PDFs)

Pillow (PIL) (manipulação de imagens para ícones e logos)

Funcionalidades principais:

Interface simples e intuitiva para usuários leigos.

Controle de tamanho máximo por arquivo via slider ou input.

Log interativo para acompanhar o andamento do processamento.

Compactação silenciosa, sem abrir janelas de terminal para cada arquivo.

Como usar:

Instale as dependências (pip install PyPDF2 Pillow).

Instale Ghostscript e adicione ao PATH do sistema.

Execute python seu_arquivo.py.

Selecione a pasta de PDFs e defina o tamanho máximo.

Clique em "Iniciar Compactação" e acompanhe os logs.

Observações:

Limite máximo recomendado para tamanho de arquivo: 20 MB.

Projetado para Windows, mas pode funcionar em Linux/Mac ajustando o caminho do Ghostscript.
