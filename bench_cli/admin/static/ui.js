// bench admin — ui.js
// Vanilla JS component library: Modal, Toast

class Modal {
  constructor(id) {
    this.el = document.getElementById(id)
    if (!this.el) throw new Error(`Modal #${id} not found`)

    // Close on backdrop click
    this.el.addEventListener('click', e => {
      if (e.target === this.el) this.close()
    })

    // Close on Escape
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && this.isOpen()) this.close()
    })

    // Close buttons
    this.el.querySelectorAll('[data-modal-close]').forEach(btn => {
      btn.addEventListener('click', () => this.close())
    })
  }

  isOpen() { return this.el.classList.contains('is-open') }

  open() {
    this.el.classList.add('is-open')
    document.body.style.overflow = 'hidden'
    const first = this.el.querySelector('input:not([type=hidden]), select, textarea')
    if (first) setTimeout(() => first.focus(), 50)
  }

  close() {
    this.el.classList.remove('is-open')
    document.body.style.overflow = ''
  }
}

class Toast {
  static show(message, type = 'info', duration = 4000) {
    const el = document.createElement('div')
    el.className = `toast toast-${type}`
    el.textContent = message
    Toast._container().appendChild(el)
    // Double rAF ensures transition fires after element is painted
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('is-visible')))
    setTimeout(() => {
      el.classList.remove('is-visible')
      el.addEventListener('transitionend', () => el.remove(), { once: true })
    }, duration)
  }

  static _container() {
    let c = document.getElementById('toast-container')
    if (!c) {
      c = document.createElement('div')
      c.id = 'toast-container'
      document.body.appendChild(c)
    }
    return c
  }
}
