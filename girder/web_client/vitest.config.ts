import { fileURLToPath } from 'node:url'
import { mergeConfig } from 'vite'
import { configDefaults, defineConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      environment: 'jsdom',
      // exclude: [...configDefaults.exclude, 'e2e/*'],
      exclude: [...configDefaults.exclude],
      root: fileURLToPath(new URL('./', import.meta.url)),
      transformMode: {
        web: [/\.[jt]sx$/],
      },
      coverage: {
        provider: 'istanbul',
      },
      // browser: {
      //   enabled: true,
      //   name: 'chrome',
      // },
    },
  })
)
