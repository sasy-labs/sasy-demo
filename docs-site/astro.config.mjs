// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

export default defineConfig({
  integrations: [
    starlight({
      title: 'SASY Policy Demo',
      social: [
        {
          icon: 'github',
          label: 'GitHub',
          href: 'https://github.com/sasy-labs/sasy-demo',
        },
      ],
      sidebar: [
        {
          label: 'Getting Started',
          items: [
            { label: 'Quick Start', slug: 'quickstart' },
            { label: 'Translate a Policy', slug: 'translate' },
          ],
        },
        {
          label: 'Policy',
          items: [
            { label: 'Policy Walkthrough', slug: 'policy/walkthrough' },
            { label: 'Confidence Report', slug: 'policy/confidence' },
          ],
        },
        {
          label: 'Demo',
          items: [
            { label: 'Scenarios', slug: 'demo/scenarios' },
            { label: 'How Enforcement Works', slug: 'demo/enforcement' },
          ],
        },
      ],
    }),
  ],
});
