import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

const openModals: HTMLDialogElement[] = []

HTMLDialogElement.prototype.showModal = function showModal(
  this: HTMLDialogElement,
) {
  this.open = true
  openModals.push(this)
}

HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
  if (!this.open) return
  this.open = false
  openModals.splice(openModals.indexOf(this), 1)
  this.dispatchEvent(new Event('close'))
}

document.addEventListener('keydown', (event) => {
  const dialog = openModals.at(-1)
  if (event.key !== 'Escape' || !dialog) return
  if (dialog.dispatchEvent(new Event('cancel', { cancelable: true })))
    dialog.close()
})

afterEach(cleanup)
