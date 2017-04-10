export default {
    'width': 894,
    'height': 673,
    'padding': 'strict',
    'data': [
        {
            'name': 'table',
            'values': [],
            'transform': [
                {
                    'type': 'filter',
                    'test': 'datum.elapsed > 0'
                },
                {
                    'type': 'aggregate',
                    'groupby': ['id', 'title', 'currentStatus'],
                    'summarize': [
                        {
                            'field': 'elapsed',
                            'ops': ['sum'],
                            'as': ['sum_y']
                        }
                    ]
                }
            ]
        }
    ],
    'scales': [
        {
            'name': 'x',
            'type': 'ordinal',
            'points': true,
            'range': 'width',
            'domain': {
                'data': 'table',
                'field': 'id'
            }
        },
        {
            'name': 'y',
            'type': 'sqrt',
            'range': 'height',
            'domain': {
                'fields': [
                    {
                        'data': 'table',
                        'field': 'sum_y'
                    }
                ]
            }
        },
        {
            'name': 'xlabels2',
            'type': 'ordinal',
            'domain': [],
            'range': []
        },
        {
            'name': 'xlabels',
            'type': 'ordinal',
            'domain': [],
            'range': []
        },
        {
            'name': 'timing',
            'type': 'ordinal',
            'domain': [],
            'range': []
        }
    ],
    'axes': [
        {
            'type': 'x',
            'scale': 'x',
            'orient': 'top',
            'properties': {
                'labels': {
                    'text': { 'scale': 'xlabels2' },
                    'angle': { 'value': -50 },
                    'align': { 'value': 'left' },
                    'itemName': { 'value': 'xlabel2' }
                }
            },
            'offset': 10
        },
        {
            'type': 'x',
            'scale': 'x',
            'orient': 'bottom',
            'subdivide': 3,
            'properties': {
                'labels': {
                    'text': { 'scale': 'xlabels' },
                    'angle': { 'value': 50 },
                    'align': { 'value': 'left' },
                    'itemName': { 'value': 'xlabel' }
                }
            }
        },
        {
            'type': 'y',
            'scale': 'y',
            'format': 's',
            'title': 'seconds',
            'properties': {
                'labels': {
                    'itemName': {
                        'value': 'ylabel'
                    },
                    'text': { 'template': '{{datum.label|slice:0,-1}}' }
                }
            }
        }
    ],
    'signals': [
        {
            'name': 'hover',
            'init': {
                'pos': {},
                'datum': {}
            },
            'streams': [
                {
                    'type': '@circle:mousemove',
                    'expr': '{ pos: {x: eventX(), y: eventY()}, datum:datum}'
                },
                {
                    'type': '@circle:mouseout',
                    'expr': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'tt0',
            'init': {},
            'expr': '{ title:hover.datum.title, sum_y:hover.datum["sum_y"] }'
        },
        {
            'name': 'tt1',
            'init': {},
            'expr': '{ sum_y:!tt0.sum_y?"":timeFormat(tt0.sum_y>3600000? "%H:%M:%S.%Ls":(tt0.sum_y>60000?"%M:%S.%Ls":"%S.%Ls"), datetime(0,0,0,0,0,0,tt0.sum_y)) }'
        },
        {
            'name': 'tt2',
            'init': {},
            'expr': '{ width:!tt0.title?0:max(tt0.title.length, tt1.sum_y.length)*7 }'
        },
        {
            'name': 'tooltip',
            'init': {},
            'expr': '{ y:hover.pos.y+30, x:(hover.pos.x>width-tt2.width+5?hover.pos.x-tt2.width-5:hover.pos.x+5), width:tt2.width, title:tt0.title, sum_y:tt1.sum_y }'
        }
    ],
    'marks': [
        {
            'type': 'line',
            'name': '',
            'from': {
                'data': 'table'
            },
            'properties': {
                'enter': {
                    'x': {
                        'scale': 'x',
                        'field': 'id'
                    },
                    'y': {
                        'scale': 'y',
                        'field': 'sum_y'
                    },
                    'itemName': {
                        'value': 'line'
                    },
                    'strokeWidth': { 'value': 2 },
                    'stroke': { 'value': '#4682b4' },
                    'dx': { 'value': 50 }
                },
                'update': {
                    'fillOpacity': {
                        'value': 1
                    }
                },
                'hover': {
                    'fillOpacity': {
                        'value': 0.5
                    }
                }
            }
        },
        {
            'type': 'symbol',
            'name': 'circle',
            'shape': 'circle',
            'from': {
                'data': 'table'
            },
            'properties': {
                'enter': {
                    'x': {
                        'scale': 'x',
                        'field': 'id'
                    },
                    'y': {
                        'scale': 'y',
                        'field': 'sum_y'
                    },
                    'itemName': {
                        'value': 'circle'
                    },
                    'strokeWidth': { 'value': 1 },
                    'fill': { 'value': '#1F77B4' },
                    'cursor': { 'value': 'pointer' }
                },
                'update': {
                    'fillOpacity': {
                        'value': 1
                    },
                    'size': { 'value': 30 },
                    'stroke': { 'value': '#1F77B4' }
                },
                'hover': {
                    'size': { 'value': 85 },
                    'stroke': { 'value': 'white' }
                }
            }
        },
        {
            'type': 'group',
            'properties': {
                'update': {
                    'x': { 'signal': 'tooltip.x' },
                    'y': { 'signal': 'tooltip.y' },
                    'width': { 'signal': 'tooltip.width' },
                    'height': { 'value': 37 },
                    'fill': { 'value': '#fff' },
                    'fillOpacity': { 'value': 1 },
                    'stroke': { 'value': '#aaa' },
                    'strokeWidth': { 'value': 0.5 }
                }
            },
            'marks': [
                {
                    'name': 'title',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 14 },
                            'text': { 'signal': 'tooltip.title' },
                            'fill': { 'value': 'black' }
                        }
                    }
                },
                {
                    'name': 'elapsed',
                    'type': 'text',
                    'properties': {
                        'update': {
                            'x': { 'value': 6 },
                            'y': { 'value': 30 },
                            'text': { 'signal': 'tooltip.sum_y' },
                            'fill': { 'value': 'black' },
                            'fontWeight': { 'value': 'bold' }
                        }
                    }
                }
            ]
        }
    ],
    'legends': [
        {
            'fill': 'timing',
            'title': 'Timings',
            'offset': -3,
            'properties': {
                'title': {
                    'dx': { 'value': 13 },
                    'fontSize': { 'value': 12 }
                },
                'symbols': {
                    'opacity': { 'value': 0 }
                },
                'labels': {
                    'fontSize': { 'value': 12 }
                }
            }
        }
    ]
};
