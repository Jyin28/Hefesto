declare module 'plotly.js-basic-dist-min' {
  const plotly: {
    newPlot: (element: HTMLDivElement, data: object[], layout: object, config: object) => Promise<unknown>
    purge: (element: HTMLDivElement) => void
  }
  export default plotly
}
