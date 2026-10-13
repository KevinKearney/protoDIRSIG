// Study patch for the Typst route (docs/study/README.md): long tables break across pages, in a smaller font.
#show figure.where(kind: table): set block(breakable: true)
#show table: set text(size: 7pt)
#set table(inset: 3pt)
