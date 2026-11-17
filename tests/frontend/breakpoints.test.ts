/**
 * Guard the responsive policy from STYLE.md by scanning the frontend sources.
 *
 * Tailwind's default breakpoints are the whole vocabulary: no theme overrides, no
 * arbitrary variants, nothing past `xl`, and no hand-written media queries. Linters
 * do not flag any of these, so the check lives here.
 */
import { readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const FRONTEND = join(process.cwd(), 'src/frontend')
const SOURCE_EXTENSIONS = ['.vue', '.ts', '.js', '.css']
const BANNED = [/2xl:/, /\bmax-\[/, /\bmin-\[/, /--breakpoint-/, /@media/]
const COMMENT_OPENERS = ['//', '*', '/*', '<!--']

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)

    if (entry.isDirectory()) return sourceFiles(path)
    return SOURCE_EXTENSIONS.some((extension) => entry.name.endsWith(extension)) ? [path] : []
  })
}

function isComment(line: string): boolean {
  const trimmed = line.trim()

  return COMMENT_OPENERS.some((opener) => trimmed.startsWith(opener))
}

describe('responsive breakpoints', () => {
  const files = sourceFiles(FRONTEND)

  it('scans the frontend sources', () => {
    expect(files.length).toBeGreaterThan(10)
  })

  it('uses only the default breakpoints below 2xl', () => {
    const violations = files.flatMap((path) =>
      readFileSync(path, 'utf8')
        .split('\n')
        .flatMap((line, index) =>
          isComment(line)
            ? []
            : BANNED.filter((pattern) => pattern.test(line)).map(
                (pattern) => `${path}:${index + 1}: ${pattern.source} in ${line.trim()}`,
              ),
        ),
    )

    expect(violations).toEqual([])
  })
})
