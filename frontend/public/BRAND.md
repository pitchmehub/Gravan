# Pitch.me — Identidade Visual & Prompts para IA

Este documento contém **dois ativos** para reprodução da identidade visual em outras IAs
(ChatGPT, Midjourney, DALL-E, Leonardo, Ideogram, Figma AI, etc.):

1. Os **arquivos SVG** prontos do favicon e do logotipo (em `/frontend/public/icons/`)
2. **Prompts textuais** para regerar/variar a identidade em IAs generativas

---

## 1. Cores & Tipografia

| Elemento           | Valor                                      |
|--------------------|--------------------------------------------|
| Cor primária       | **#E11D48** (Rose 600 — vermelho-carmim)   |
| Cor secundária     | **#0A0A0A** (preto quase absoluto)         |
| Fundo neutro       | **#FFFFFF**                                |
| Tipografia wordmark | Inter / IBM Plex Sans — peso **800 (ExtraBold)**, letter-spacing −3 |
| Raio do cantinho   | 20% do lado (rounded-square: 104px em 512px) |

---

## 2. Símbolo (mark)

**Conceito:** um quadrado arredondado vermelho-carmim com **4 barras verticais brancas em altura crescente** (equalizer de pitch ascendente) e um pequeno círculo branco acima da barra mais alta (o "ponto" do `.me`).

**Metáfora:**
- Barras crescentes = tom (pitch) subindo
- Círculo superior = vocal/microfone + o "ponto" do domínio `.me`
- Quadrado arredondado = app-icon moderno, minimalista

### 2.1 Prompt para IA generativa (imagem — DALL·E 3, Midjourney, Ideogram, Leonardo)

```
Minimalist flat app icon for a music marketplace brand called "Pitch.me". Rounded-square container (corner radius 20%) filled with deep rose-red color hex #E11D48. Inside, four pure-white vertical bars arranged horizontally, each bar with slightly rounded ends. Each bar is taller than the previous one (ascending equalizer / pitch rising). Above the tallest bar, a single small white circle represents the "." (dot). Clean geometric Bauhaus style, no gradients, no shadows, no texture, perfectly centered, high contrast. Vector-style, solid colors only. White background outside the icon. 1024×1024.
```

### 2.2 Negative prompt (se a IA aceitar — Leonardo, Stable Diffusion)

```
3D, gradient, realistic, photograph, musical instrument, person, guitar, headphones, text, letters, watermark, noise, drop shadow, glow, blurry, off-center
```

---

## 3. Logotipo (mark + wordmark lado a lado)

**Conceito:** mark à esquerda + palavra "Pitch" em preto + ".me" no vermelho-carmim.

### 3.1 Prompt para IA generativa

```
Horizontal logo lockup for "Pitch.me" — on the left: a rounded-square icon with four ascending white bars and a small white dot on solid #E11D48 rose-red background. On the right: the wordmark "Pitch.me" in Inter ExtraBold sans-serif, letter-spacing tight, with "Pitch" in near-black (#0A0A0A) and ".me" in the same rose-red #E11D48 as the icon. Flat, minimalist, Swiss design, white background, professional SaaS branding. 1800×480.
```

---

## 4. Variação para fundo escuro (dark mode)

```
Same Pitch.me logo, but on deep navy background #0A0A0A. The icon keeps #E11D48 fill with white bars/dot. The wordmark "Pitch" is in white, and ".me" in the signature #E11D48 rose-red. Crisp, modern, premium.
```

---

## 5. Outputs / Tamanhos sugeridos

| Arquivo                  | Tamanho       | Uso                        |
|--------------------------|---------------|----------------------------|
| `favicon.svg`            | vetor         | Favicon moderno (browsers) |
| `favicon.ico`            | 16/32/48 px   | Favicon legado             |
| `favicon-32.png`         | 32×32         | Abas do navegador          |
| `apple-touch-icon.png`   | 180×180       | iOS homescreen             |
| `icon-192.png`           | 192×192       | PWA / Android              |
| `icon-512.png`           | 512×512       | PWA splash, lojas de apps  |
| `logo.svg` / `logo.png`  | horizontal    | Header do site, cards      |

Todos os arquivos estão em `/frontend/public/icons/` (e os principais estão replicados
na raiz `/frontend/public/` para compatibilidade com navegadores antigos).

---

## 6. Usar como referência visual (image-to-image)

Para regerar/evoluir o logo em ferramentas como **Midjourney** ou **Ideogram** que aceitam
imagem de referência, suba o arquivo `logo.png` junto do prompt e adicione:

```
--sref https://SEU_DOMINIO/icons/logo.png --sw 200 --stylize 100
```

(Ou o equivalente na sua IA: "use this image as style reference, keep color palette and
geometric minimalism, change only [arrangement/typography/shape]").

---

## 7. Regras de uso da marca

- Sempre preservar o espaçamento em torno do mark (mínimo = altura de uma barra).
- Nunca girar o mark.
- Nunca aplicar gradiente no fundo do mark (quebra a identidade flat).
- Use o vermelho-carmim somente em elementos de ação (CTAs, links, destaques) e no wordmark.
- Para estampas em mídia impressa, converter #E11D48 para **CMYK ~0 / 85 / 60 / 0** ou Pantone **199 C**.
