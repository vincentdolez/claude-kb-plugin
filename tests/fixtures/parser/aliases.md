# Test aliases

<!-- Variante 1: sans alias -->
[[00-fondations/principes]] doit passer (lien simple, cible existe)

<!-- Variante 2: alias normal avec pipe -->
[[00-fondations/principes|Principes]] doit passer (alias normal)

<!-- Variante 3: alias échappé avec \| (syntaxe Obsidian dans tableaux Markdown) -->
| Col1 | Col2 |
|---|---|
| [[00-fondations/principes\|Lien tableau]] | valeur |

<!-- Variante 4: anchor + alias -->
[[02-marque/convictions#Préambule|Convictions]] doit passer (anchor + alias)

<!-- Variante 5: lien cassé avec alias (doit rester cassé) -->
[[fichier-inexistant\|alias]] doit rester cassé
[[disparu|alias normal]] doit rester cassé
