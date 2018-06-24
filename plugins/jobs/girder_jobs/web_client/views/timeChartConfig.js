const timeChartConfig = {
    'width': 894,
    'height': 673,
    'autosize': 'fit',
    'data': [
        {
            'name': 'table',
            'values': [],
            'transform': [
                {
                    'type': 'filter',
                    'expr': 'datum.elapsed > 0'
                },
                {
                    'type': 'aggregate',
                    'groupby': ['id', 'title', 'currentStatus'],
                    'fields': ['elapsed'],
                    'ops': ['sum'],
                    'as': ['sum_y']
                },
                {
                    'type': 'formula',
                    'as': 'adjSum_y',
                    'expr': 'datum.sum_y/1000'
                }
            ]
        }
    ],
    'scales': [
        {
            'name': 'x',
            'type': 'point',
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
                        'field': 'adjSum_y'
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
            'scale': 'x',
            'orient': 'top',
            'encode': {
                'labels': {
                    'update': {
                        'text': { 'field': 'value', 'scale': 'xlabels2' },
                        'angle': { 'value': -50 },
                        'align': { 'value': 'left' },
                        'itemName': { 'value': 'xlabel2' }
                    }
                }
            },
            'offset': 10
        },
        {
            'scale': 'x',
            'orient': 'bottom',
            'encode': {
                'labels': {
                    'update': {
                        'text': { 'field': 'value', 'scale': 'xlabels' },
                        'angle': { 'value': 50 },
                        'align': { 'value': 'left' },
                        'itemName': { 'value': 'xlabel' }
                    }
                }
            }
        },
        {
            'orient': 'left',
            'scale': 'y',
            'format': 's',
            'title': 'seconds',
            'encode': {
                'labels': {
                    'itemName': { 'value': 'ylabel' }
                }
            }
        }
    ],
    'signals': [
        {
            'name': 'hover',
            'value': {
                'pos': {},
                'datum': {}
            },
            'on': [
                {
                    'events': '@circle:mousemove',
                    'update': '{ pos: {x: x(), y: y()}, datum:datum}'
                },
                {
                    'events': '@circle:mouseout',
                    'update': '{pos:{},datum:{}}'
                }
            ]
        },
        {
            'name': 'tt0',
            'value': {},
            'update': '{ title:hover.datum.title, sum_y:hover.datum["sum_y"] }'
        },
        {
            'name': 'tt1',
            'value': {},
            'update': '{ sum_y: ' +
                '!tt0.sum_y ? "" : ' +
                'floor(tt0.sum_y/(' +
                '  tt0.sum_y >= 3600000 ? 3600000 : (' +
                '    tt0.sum_y >= 60000 ? 60000 : 1000))) + ' +
                'timeFormat(datetime(0,0,0,0,0,0,tt0.sum_y), ' +
                '  tt0.sum_y >= 3600000 ? ":%M:%S.%L": (' +
                '    tt0.sum_y >= 60000 ? ":%S.%L" : ".%Ls")) }'
        },
        {
            'name': 'tt2',
            'value': {},
            'update': '{ width:!tt0.title?0:max(tt0.title.length, tt1.sum_y.length)*7 }'
        },
        {
            'name': 'tooltip',
            'value': {},
            'update': '{ y:hover.pos.y+30, x:(hover.pos.x>width-tt2.width+5?hover.pos.x-tt2.width-5:hover.pos.x+5), width:tt2.width, title:tt0.title, sum_y:tt1.sum_y }'
        }
    ],
    'marks': [
        {
            'type': 'line',
            'name': '',
            'from': {
                'data': 'table'
            },
            'encode': {
                'enter': {
                    'x': {
                        'scale': 'x',
                        'field': 'id'
                    },
                    'y': {
                        'scale': 'y',
                        'field': 'adjSum_y'
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
            'encode': {
                'enter': {
                    'x': {
                        'scale': 'x',
                        'field': 'id'
                    },
                    'y': {
                        'scale': 'y',
                        'field': 'adjSum_y'
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
            'encode': {
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
                    'encode': {
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
                    'encode': {
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
            'title': 'Status',
            'offset': 20,
            'encode': {
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

export default timeChartConfig;
