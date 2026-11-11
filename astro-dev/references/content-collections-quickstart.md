# Content Collections — Quickstart

## 1. Define the collection

`src/content.config.ts` (project root, *not* inside `src/content/`):

```ts
import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const skills = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/skills' }),
  schema: z.object({
    title: z.string(),
    tagline: z.string(),
    category: z.enum(['workflow', 'framework', 'language']),
  }),
});

export const collections = { skills };
```

## 2. Add entries

Each file in `src/content/skills/` becomes one entry. Its `id` is the
filename (without extension) unless the loader generates one
differently — for `glob`, it's the file path relative to `base`.

```md
---
title: "Git Commits"
tagline: "Conventional commits and PR descriptions"
category: workflow
---

Longer description rendered as the entry body.
```

## 3. List entries

```astro
---
import { getCollection } from 'astro:content';
const skills = await getCollection('skills');
---
<ul>
  {skills.map((skill) => (
    <li><a href={`/skills/${skill.id}/`}>{skill.data.title}</a></li>
  ))}
</ul>
```

## 4. Dynamic detail page

`src/pages/skills/[id].astro`:

```astro
---
import { getCollection, render } from 'astro:content';

export async function getStaticPaths() {
  const skills = await getCollection('skills');
  return skills.map((skill) => ({
    params: { id: skill.id },
    props: { skill },
  }));
}

const { skill } = Astro.props;
const { Content } = await render(skill);
---
<Content />
```

## Gotchas

- Schema validation errors point to the exact field and file — read
  the build error before assuming the loader is broken.
- Changing the `base` path or `pattern` requires a dev server restart
  in some setups; if a file you just added isn't picked up, restart
  before debugging further.
- `z.coerce.date()` accepts string dates from frontmatter and converts
  them to `Date` objects — use it instead of `z.date()` if your
  frontmatter writes dates as plain strings (which it almost always
  does).
