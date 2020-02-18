export default {
    install (Vue) {
        Vue.prototype.$generatePaletteFromString = (str, count, full = false) => {
            const results = ColorTool.generatePaletteFromString(str, count)
            return full ? results : results.colors
        }
        Vue.prototype.$createColorPalette = (count) => {
            return ColorTool.generatePaletteFromString(count)
        }
        Vue.prototype.$getTextColor = (hex) => {
            return ColorTool.getTextColor(hex)
        }
    }
}

const ColorTool = {
    getTextColor: function (hex) {
        if (hex === undefined) {
            return "black"
        } else {
            hex = hex.slice(1)
            var r = parseInt(hex.substring(0, 2), 16)
            var g = parseInt(hex.substring(2, 4), 16)
            var b = parseInt(hex.substring(4, 6), 16)
            var avg = ((2 * r) + b + (3 * g)) / 6
            if (avg < 128) {
                return "white"
            } else {
                return "black"
            }
        }
    },

    // pass the number of distinct colours to receive an array of colours
    createColorPalette: function (count) {
        const interval = 1 / count
        let colours = []
        for (let i = 0; i < count; i++) {
            colours.push(ColorTool.HSVtoRGB([interval * i, 1, 1]))
        }
        return colours
    },

    HSVtoRGB: function (hsv) {
        let [H, S, V] = hsv
        // 1
        H *= 6
        // 2
        const I = Math.floor(H)
        const F = H - I
        // 3
        const M = V * (1 - S)
        const N = V * (1 - S * F)
        const K = V * (1 - S * (1 - F))
        // 4
        let R, G, B
        switch (I) {
        case 0:
            [R, G, B] = [V, K, M]
            break
        case 1:
            [R, G, B] = [N, V, M]
            break
        case 2:
            [R, G, B] = [M, V, K]
            break
        case 3:
            [R, G, B] = [M, N, V]
            break
        case 4:
            [R, G, B] = [K, M, V]
            break
        case 5:
        case 6: // for when H=1 is given
            [R, G, B] = [V, M, N]
            break
        }
        return ColorTool.convertToHex([R, G, B])
    },

    convertToHex: function (channels) {
        let colour = "#"
        channels.forEach(chan => {
            chan = Math.round(chan * 255).toString(16)
            if (chan.length === 1) {
                chan = "0" + chan
            }
            colour += chan
        })
        return colour
    },

    // pass the element's id from the list along to get a colour for a single item
    generatePaletteFromString: function (str, items, onlySpecific = false) {
        const hue = ColorTool.__stringToNumber(str)
        const saturation = 1
        const steps = 80 / items
        let colors = []
        let results = {}
        results.stringToNumber = hue
        results.hue = hue
        results.saturation = saturation
        results.steps = steps
        if (onlySpecific !== false && !isNaN(onlySpecific)) {
            let value = (20 + (steps * (onlySpecific + 1))) / 100
            return ColorTool.HSVtoRGB([hue, saturation, value])
        }
        for (let i = 0; i < items; i++) {
            let value = (20 + (steps * (i + 1))) / 100
            let rgb = ColorTool.HSVtoRGB([hue, saturation, value])
            colors.push(rgb)
        }
        results.colors = colors
        return results
    },

    __stringToNumber: function (str) {
    // str = mb_convert_encoding(str, 'ASCII'); -- PHP function
    // const strUpper = str.toUpperCase()
        const strUpper = str
        let number = 0
        for (let i = 0; i < strUpper.length; i++) {
            // number += str.charCodeAt(i) * Math.pow(10, str.length-1-i);
            number += str.charCodeAt(i)
            // number += (strUpper.charCodeAt(i) - 65) / 26 * 100;
        }
        // console.log(number)
        // console.log(number % 100)
        // console.log(number % 100 / 100)
        return number % 100 / 100
    }
}
