# Test code-fences

Ce wiki-link hors code-fence doit être détecté : [[00-fondations/principes]]

```markdown
Ce wiki-link dans un bloc triple backtick doit être ignoré : [[placeholder]]
[[chemin/fichier]] aussi ignoré
```

Ce lien après le bloc doit passer : [[02-marque/convictions]]

~~~
Ce bloc tilde doit aussi être ignoré : [[autre-placeholder]]
~~~

Et un lien en inline code `[[X]]` doit être conservé (single backtick).

Lien cassé hors fence (doit rester cassé) : [[vraiment-inexistant]]
