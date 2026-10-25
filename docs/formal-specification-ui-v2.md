# Formal Specification — AI-VoiceUsage UI v2

## Objetivo
Preservar o contador de voz minimalista e acrescentar uma janela opcional para visualizar **quando o tempo utilizado deixará de contar** na janela móvel de 24 horas.

## Interface principal
- Manter cronômetro grande `HH:MM:SS` e botão Start/Stop.
- Manter alternância Dark/Light já implementada, com paleta azul.
- Acrescentar um botão discreto **Statistics**, que abre uma janela separada.
- Sliding window fixa em 24 horas; não exibir campo de configuração.
- Manter persistência SQLite e comportamento do Start/Stop sem mudanças.

## Janela Statistics
- Implementar usando **Tkinter Canvas**, sem Matplotlib nem outros frameworks.
- Exibir **um único gráfico** com eixo X de `agora` até `agora + 24h`.
- Eixo X: horários locais `HH:MM`, nunca offsets `+Nh`; destacar principalmente instantes de término de recuperação (`fim_da_sessão + 24h`).
- Ocultar rótulos X que se sobreponham, mas nunca alterar dados do gráfico.
- Eixo Y: tempo usado, de zero a um limite visual suficiente para o uso atual; poucas marcas simples.
- Curva **contínua por trechos**: horizontal quando o uso não muda, linear decrescente enquanto parte de uma sessão sai da janela; sem degraus artificiais e sem interpolação de dados ausentes.
- O gráfico deve reagir à mudança de tema, ao redimensionamento e à passagem do tempo.
- Se a janela já estiver aberta, o botão deve trazê-la para frente, sem criar duplicatas.

## Modelo
Para cada sessão `[s,e]` e instante futuro `t`, a parcela contabilizada é `max(0, min(e,t) - max(s,t-24h))`. O total é a soma das parcelas. Basta calcular vértices nos pontos `s+24h` e `e+24h` e conectar linearmente.
A previsão considera que nenhuma nova sessão será criada. Se uma sessão estiver ativa, seu fim projetado é **agora**; a previsão muda conforme a gravação continua. O software não consulta a cota oficial do ChatGPT.

## Fora de escopo
Quota e tempo restante; editor de janela móvel; gráficos históricos adicionais; outros formatos de configuração; animações; dependências externas; UI muito elaborada.

## Critérios de aceitação
1. Contador e persistência permanecem funcionais e a janela principal segue compacta.
2. Dark/Light vale para ambas as janelas.
3. O gráfico começa no uso atual, é não crescente na ausência de novas sessões e chega a zero em até 24 horas.
4. Ticks X representam eventos de recuperação; horários legíveis sem sobreposição excessiva.
5. Novos testes unitários cobrem vazio, início/fim de recuperação e sessão ativa.
6. Python Standard Library apenas, sem mudanças no empacotamento existente.
