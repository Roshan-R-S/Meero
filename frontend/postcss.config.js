const isVitest = process.env.VITEST === 'true'

export default {
  plugins: isVitest
    ? {}
    : {
        '@tailwindcss/postcss': {},
        autoprefixer: {},
      },
}
