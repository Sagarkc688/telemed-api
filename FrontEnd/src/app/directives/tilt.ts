import { Directive, ElementRef, HostListener } from '@angular/core';

// Add appTilt to any element to make it tilt towards the mouse in 3D
@Directive({
  selector: '[appTilt]'
})
export class Tilt {
  private maxTilt = 8;   // how far it can tilt, in degrees

  // respect users who turn off animations in their computer settings
  private reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  constructor(private el: ElementRef) {}

  @HostListener('mousemove', ['$event'])
  onMouseMove(event: MouseEvent) {
    if (this.reduceMotion) {
      return;
    }
    // where is the mouse inside the element? -0.5 (left/top) to 0.5 (right/bottom)
    const box = this.el.nativeElement.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;

    this.el.nativeElement.style.transform =
      'perspective(800px) rotateX(' + (-y * this.maxTilt) + 'deg) rotateY(' + (x * this.maxTilt) + 'deg) translateY(-4px)';
  }

  @HostListener('mouseleave')
  onMouseLeave() {
    this.el.nativeElement.style.transform = '';   // back to flat
  }
}