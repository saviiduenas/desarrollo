# -*- coding: utf-8 -*-

import time
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, _
import requests
import logging
import base64
from lxml import etree
from lxml.builder import ElementMaker
import xml.etree.ElementTree as ET
import datetime

class AccountMove(models.Model):
    _inherit = "account.move"

    fel_numero_autorizacion = fields.Char('Feel Numero de autorizacion')
    fel_serie = fields.Char('Feel serie')
    fel_numero = fields.Char('Feel numero')
    # fel_uuid = fields.Char('UUID')
    fel_documento_certificado = fields.Char('Documento Feel')
    fel_incoterm = fields.Selection([
            ('EXW', 'En fábrica'),
            ('FCA', 'Libre transportista'),
            ('FAS', 'Libre al costado del buque'),
            ('FOB', 'Libre a bordo'),
            ('CFR', 'Costo y flete'),
            ('CIF','Costo, seguro y flete'),
            ('CPT','Flete pagado hasta'),
            ('CIP','Flete y seguro pagado hasta'),
            ('DDP','Entregado en destino con derechos pagados'),
            ('DAP','Entregada en lugar'),
            ('DAT','Entregada en terminal'),
            ('ZZZ','Otros')
        ],string="Incoterm",default="EXW",
        help="Termino de entrega")
    tipo_factura = fields.Selection([('venta','Venta'),('compra', 'Compra o Bien'), ('servicio', 'Servicio'),('varios','Varios'), ('combustible', 'Combustible'),('importacion', 'Importación'),('exportacion','Exportación')],
        string="Tipo de factura")

# 4 1 , exportacion
    def fecha_hora_factura(self, fecha):
        fecha_convertida = datetime.datetime.strptime(str(fecha), '%Y-%m-%d').date().strftime('%Y-%m-%d')
        hora = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%H:%M:%S")
        fecha_hora_emision = str(fecha_convertida)+'T'+str(hora)
        return fecha_hora_emision

    def _post(self,soft=True):
        for factura in self:
            if factura.journal_id and factura.move_type == 'out_invoice' and factura.journal_id.fel_tipo_dte and factura.journal_id.fel_codigo_establecimiento and factura.company_id.fel_usuario and factura.company_id.fel_llave_firma:
                logging.warn(factura)
                # Definimos SHEMALOCATION
                lista_impuestos = []

                attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
                DTE_NS = "{http://www.sat.gob.gt/dte/fel/0.2.0}"
                # Nuevo SMAP
                NSMAP = {
                    "ds": "http://www.w3.org/2000/09/xmldsig#",
                    "dte": "http://www.sat.gob.gt/dte/fel/0.2.0",
                    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
                }
                moneda = str(factura.currency_id.name)
                logging.warn(moneda)
                fecha = datetime.datetime.strptime(str(factura.invoice_date), '%Y-%m-%d').date().strftime('%Y-%m-%d')
                hora = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%H:%M:%S")
                fecha_hora_emision = self.fecha_hora_factura(factura.invoice_date)
                tipo = factura.journal_id.fel_tipo_dte
                # if tipo == 'FACT':
                #
                # if tipo == 'NDEB':
                #
                if tipo == 'NCRE':
                    factura_original_id = self.env['account.invoice'].search([('number','=',factura.origin)])
                    if factura_original_id and factura.currency_id.id == factura_original_id.currency_id.id:
                        tipo == 'NCRE'
                        logging.warn('si es nota credito')
                    else:
                        raise UserError(str('NOTA DE CREDITO DEBE DE SER CON LA MISMA MONEDA QUE LA FACTURA ORIGINAL'))

                datos_generales = {
                    "CodigoMoneda": moneda,
                    "FechaHoraEmision":fecha_hora_emision,
                    "NumeroAcceso": str(100000000),
                    "Tipo":tipo
                    }
                if tipo == 'FACT' and factura.tipo_factura == "exportacion":
                    datos_generales['Exp'] = "SI"



                nit_company = "CF"
                if '-' in factura.company_id.vat:
                    nit_company = factura.company_id.vat.replace('-','')
                else:
                    nit_company = factura.company_id.vat

                datos_emisor = {
                    "AfiliacionIVA":"GEN",
                    "CodigoEstablecimiento": str(factura.journal_id.fel_codigo_establecimiento) or "",
                    "CorreoEmisor": str(factura.company_id.email) or "",
                    "NITEmisor": str(nit_company),
                    # "NITEmisor": '103480307',
                    "NombreComercial": factura.journal_id.fel_nombre_comercial or "",
                    "NombreEmisor": factura.company_id.name or ""
                }

                nit_partner = "CF"
                if factura.partner_id.vat:
                    if '-' in factura.partner_id.vat:
                        nit_partner = factura.partner_id.vat.replace('-','')
                    else:
                        nit_partner = factura.partner_id.vat

                datos_receptor = {
                    "CorreoReceptor": factura.partner_id.email or "",
                    "IDReceptor": str(nit_partner),
                    "NombreReceptor": factura.partner_id.name
                }


                if tipo == 'FACT' and factura.currency_id !=  factura.company_id.currency_id:
                    datos_receptor['IDReceptor'] = "CF"

                # Creamos los TAGS necesarios
                GTDocumento = etree.Element(DTE_NS+"GTDocumento", {attr_qname: 'http://www.sat.gob.gt/dte/fel/0.1.0'}, Version="0.1", nsmap=NSMAP)
                TagSAT = etree.SubElement(GTDocumento,DTE_NS+"SAT",ClaseDocumento="dte")
                TagDTE = etree.SubElement(TagSAT,DTE_NS+"DTE",ID="DatosCertificados")
                TagDatosEmision = etree.SubElement(TagDTE,DTE_NS+"DatosEmision",ID="DatosEmision")
                TagDatosGenerales = etree.SubElement(TagDatosEmision,DTE_NS+"DatosGenerales",datos_generales)
                # Datos de emisor
                TagEmisor = etree.SubElement(TagDatosEmision,DTE_NS+"Emisor",datos_emisor)
                TagDireccionEmisor = etree.SubElement(TagEmisor,DTE_NS+"DireccionEmisor",{})
                TagDireccion = etree.SubElement(TagDireccionEmisor,DTE_NS+"Direccion",{})
                TagDireccion.text = str(factura.journal_id.direccion_id.street)+" "+str(factura.journal_id.direccion_id.street2)
                TagCodigoPostal = etree.SubElement(TagDireccionEmisor,DTE_NS+"CodigoPostal",{})
                TagCodigoPostal.text = str(factura.journal_id.direccion_id.zip)
                TagMunicipio = etree.SubElement(TagDireccionEmisor,DTE_NS+"Municipio",{})
                TagMunicipio.text = str(factura.journal_id.direccion_id.city)
                TagDepartamento = etree.SubElement(TagDireccionEmisor,DTE_NS+"Departamento",{})
                TagDepartamento.text = str(factura.journal_id.direccion_id.state_id.name)
                TagPais = etree.SubElement(TagDireccionEmisor,DTE_NS+"Pais",{})
                TagPais.text = "GT"
                # Datos de receptor
                TagReceptor = etree.SubElement(TagDatosEmision,DTE_NS+"Receptor",datos_receptor)
                TagDireccionReceptor = etree.SubElement(TagReceptor,DTE_NS+"DireccionReceptor",{})
                TagReceptorDireccion = etree.SubElement(TagDireccionReceptor,DTE_NS+"Direccion",{})
                TagReceptorDireccion.text = (factura.partner_id.street or "Ciudad")+" "+(factura.partner_id.street2 or "")
                TagReceptorCodigoPostal = etree.SubElement(TagDireccionReceptor,DTE_NS+"CodigoPostal",{})
                TagReceptorCodigoPostal.text = factura.partner_id.zip or '01001'
                TagReceptorMunicipio = etree.SubElement(TagDireccionReceptor,DTE_NS+"Municipio",{})
                TagReceptorMunicipio.text = factura.partner_id.city or 'Guatemala'
                TagReceptorDepartamento = etree.SubElement(TagDireccionReceptor,DTE_NS+"Departamento",{})
                TagReceptorDepartamento.text = factura.partner_id.state_id.name or 'Guatemala'
                TagReceptorPais = etree.SubElement(TagDireccionReceptor,DTE_NS+"Pais",{})
                TagReceptorPais.text = "GT"
                # Frases

                data_frase = {
                    "xmlns:dte": "http://www.sat.gob.gt/dte/fel/0.2.0"
                }


                NSMAPFRASE = {
                    "dte": "http://www.sat.gob.gt/dte/fel/0.2.0"
                }

                if tipo not in  ['NDEB', 'NCRE']:
                    TagFrases = etree.SubElement(TagDatosEmision,DTE_NS+"Frases", {},nsmap=NSMAPFRASE)
                    for linea_frase in factura.company_id.fel_frase_ids:
                        frases_datos = {}
                        if tipo == 'FACT' and factura.currency_id !=  factura.company_id.currency_id:
                            if linea_frase.frase:
                                frases_datos = {"CodigoEscenario": linea_frase.codigo,"TipoFrase":linea_frase.frase}
                            else:
                                frases_datos = {"CodigoEscenario": linea_frase.codigo}
                        if tipo == 'FACT' and factura.currency_id ==  factura.company_id.currency_id:
                            if int(linea_frase.frase) == 4:
                                continue
                            else:
                                frases_datos = {"CodigoEscenario": linea_frase.codigo,"TipoFrase":linea_frase.frase}
                        # if tipo == 'NCRE':
                        #     if linea_frase.frase:
                        #         frases_datos = {"CodigoEscenario": linea_frase.codigo,"TipoFrase":linea_frase.frase}
                        #     else:
                        #         frases_datos = {"CodigoEscenario": linea_frase.codigo}
                        TagFrase = etree.SubElement(TagFrases,DTE_NS+"Frase",frases_datos)
                        # TagFrases.append(TagFrase)


                # Items
                TagItems = etree.SubElement(TagDatosEmision,DTE_NS+"Items",{})

                impuestos_dic = {'IVA': 0}
                tax_iva = False
                # monto_gravable_iva = 0
                # monto_impuesto_iva = 0
                for linea in factura.invoice_line_ids:
                    if linea.product_id:
                        tax_ids = linea.tax_ids
                        numero_linea = 1
                        bien_servicio = "S" if linea.product_id.type == 'service' else "B"
                        linea_datos = {
                            "BienOServicio": bien_servicio,
                            'NumeroLinea': str(numero_linea)
                        }
                        numero_linea += 1
                        TagItem =  etree.SubElement(TagItems,DTE_NS+"Item",linea_datos)

                        cantidad = linea.quantity
                        unidad_medida = "UNI"
                        descripcion = linea.product_id.name
                        # precio_unitario = (linea.price_unit * (1 - (linea.discount) / 100.0)) if linea.discount > 0 else linea.price_unit
                        precio_unitario = linea.price_unit
                        precio = linea.price_unit * linea.quantity
                        descuento = ((linea.quantity * linea.price_unit) - linea.price_total) if linea.discount > 0 else 0
                        precio_subtotal = '{:.6f}'.format(linea.price_subtotal)
                        TagCantidad = etree.SubElement(TagItem,DTE_NS+"Cantidad",{})
                        TagCantidad.text ='{:.2f}'.format(cantidad)
                        # TagCantidad.text = str(cantidad)
                        TagUnidadMedida = etree.SubElement(TagItem,DTE_NS+"UnidadMedida",{})
                        TagUnidadMedida.text = str(unidad_medida)
                        TagDescripcion = etree.SubElement(TagItem,DTE_NS+"Descripcion",{})
                        TagDescripcion.text = descripcion
                        TagPrecioUnitario = etree.SubElement(TagItem,DTE_NS+"PrecioUnitario",{})
                        TagPrecioUnitario.text = '{:.6f}'.format(precio_unitario)
                        TagPrecio = etree.SubElement(TagItem,DTE_NS+"Precio",{})
                        TagPrecio.text =  '{:.6f}'.format(precio)
                        TagDescuento = etree.SubElement(TagItem,DTE_NS+"Descuento",{})
                        TagDescuento.text =  str('{:.6f}'.format(descuento))


                        # impuestos
                        TagImpuestos = etree.SubElement(TagItem,DTE_NS+"Impuestos",{})

                        logging.warn('IMPUESTOS')
                        currency = linea.move_id.currency_id
                        logging.warn(precio_unitario)
                        taxes = tax_ids.compute_all(precio_unitario-(descuento/linea.quantity), currency, linea.quantity, linea.product_id, linea.move_id.partner_id)

                        for impuesto in taxes['taxes']:
                            nombre_impuesto = impuesto['name']
                            valor_impuesto = impuesto['amount']
                            if impuesto['name'] == 'IVA por Pagar':
                                nombre_impuesto = "IVA"
                                tax_iva = True

                            TagImpuesto = etree.SubElement(TagImpuestos,DTE_NS+"Impuesto",{})
                            TagNombreCorto = etree.SubElement(TagImpuesto,DTE_NS+"NombreCorto",{})
                            TagNombreCorto.text = nombre_impuesto
                            TagCodigoUnidadGravable = etree.SubElement(TagImpuesto,DTE_NS+"CodigoUnidadGravable",{})
                            TagCodigoUnidadGravable.text = "1"
                            TagMontoGravable = etree.SubElement(TagImpuesto,DTE_NS+"MontoGravable",{})
                            TagMontoGravable.text = str(precio_subtotal)
                            TagMontoImpuesto = etree.SubElement(TagImpuesto,DTE_NS+"MontoImpuesto",{})
                            TagMontoImpuesto.text = '{:.6f}'.format(valor_impuesto)
                            # monto_gravable_iva += precio_subtotal
                            # monto_impuesto_iva += valor_impuesto


                            lista_impuestos.append({'nombre': nombre_impuesto, 'monto': valor_impuesto})

                        if (tipo in ['FACT','NCRE']) and factura.currency_id !=  factura.company_id.currency_id:

                            TagImpuesto = etree.SubElement(TagImpuestos,DTE_NS+"Impuesto",{})
                            TagNombreCorto = etree.SubElement(TagImpuesto,DTE_NS+"NombreCorto",{})
                            TagNombreCorto.text = "IVA"
                            TagCodigoUnidadGravable = etree.SubElement(TagImpuesto,DTE_NS+"CodigoUnidadGravable",{})
                            TagCodigoUnidadGravable.text = "2"
                            TagMontoGravable = etree.SubElement(TagImpuesto,DTE_NS+"MontoGravable",{})
                            TagMontoGravable.text = str(precio_subtotal)
                            TagMontoImpuesto = etree.SubElement(TagImpuesto,DTE_NS+"MontoImpuesto",{})
                            TagMontoImpuesto.text = "0.00"


                        logging.warn(taxes)
                        TagTotal = etree.SubElement(TagItem,DTE_NS+"Total",{})
                        TagTotal.text = '{:.6f}'.format(linea.price_total)
                        # TagTotal.text =  str(linea.price_total)


                TagTotales = etree.SubElement(TagDatosEmision,DTE_NS+"Totales",{})
                TagTotalImpuestos = etree.SubElement(TagTotales,DTE_NS+"TotalImpuestos",{})

                if len(lista_impuestos) > 0:
                    total_impuesto = 0
                    logging.warn('EL IMPUESTO')
                    for i in lista_impuestos:
                        logging.warn(i)
                        total_impuesto += float(i['monto'])
                    dato_impuesto = {'NombreCorto': lista_impuestos[0]['nombre'],'TotalMontoImpuesto': str('{:.6f}'.format(total_impuesto))}
                    TagTotalImpuesto = etree.SubElement(TagTotalImpuestos,DTE_NS+"TotalImpuesto",dato_impuesto)
                    TagTotalImpuestos.append(TagTotalImpuesto)

                TagGranTotal = etree.SubElement(TagTotales,DTE_NS+"GranTotal",{})
                TagGranTotal.text = '{:.6f}'.format(factura.currency_id.round(factura.amount_total))

                if tipo == 'FACT' and factura.currency_id !=  factura.company_id.currency_id and factura.tipo_factura == "exportacion":
                    dato_impuesto = {'NombreCorto': "IVA",'TotalMontoImpuesto': str(0.00)}
                    TagTotalImpuesto = etree.SubElement(TagTotalImpuestos,DTE_NS+"TotalImpuesto",dato_impuesto)
                    TagComplementos = etree.SubElement(TagDatosEmision,DTE_NS+"Complementos",{})
                    datos_complementos = {
                        "IDComplemento": "EXPORTACION",
                        "NombreComplemento": "EXPORTACION",
                        "URIComplemento": "EXPORTACION"
                    }
                    TagComplemento = etree.SubElement(TagComplementos,DTE_NS+"Complemento",datos_complementos)
                    NSMAP = {
                        "cex": "http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0"
                    }
                    cex = "{http://www.sat.gob.gt/face2/ComplementoExportaciones/0.1.0}"

                    TagExportacion = etree.SubElement(TagComplemento,cex+"Exportacion",{},Version="1",nsmap=NSMAP)
                    TagNombreConsignatarioODestinatario = etree.SubElement(TagExportacion,cex+"NombreConsignatarioODestinatario",{})
                    TagNombreConsignatarioODestinatario.text = str(factura.partner_id.name)
                    TagDireccionConsignatarioODestinatario = etree.SubElement(TagExportacion,cex+"DireccionConsignatarioODestinatario",{})
                    TagDireccionConsignatarioODestinatario.text = str(factura.company_id.street or "")+" "+str(factura.company_id.street2 or "")
                    TagCodigoConsignatarioODestinatario = etree.SubElement(TagExportacion,cex+"CodigoConsignatarioODestinatario",{})
                    TagCodigoConsignatarioODestinatario.text = str(factura.company_id.zip or "")
                    TagNombreComprador = etree.SubElement(TagExportacion,cex+"NombreComprador",{})
                    TagNombreComprador.text = str(factura.partner_id.name)
                    TagDireccionComprador = etree.SubElement(TagExportacion,cex+"DireccionComprador",{})
                    TagDireccionComprador.text = str(factura.company_id.street or "")+" "+str(factura.company_id.street2 or "")
                    TagCodigoComprador = etree.SubElement(TagExportacion,cex+"CodigoComprador",{})
                    TagCodigoComprador.text = str(factura.company_id.zip) if factura.company_id.zip else "N/A"
                    TagOtraReferencia = etree.SubElement(TagExportacion,cex+"OtraReferencia",{})
                    TagOtraReferencia.text = "N/A"
                    TagINCOTERM = etree.SubElement(TagExportacion,cex+"INCOTERM",{})
                    TagINCOTERM.text = str(factura.fel_incoterm)
                    TagNombreExportador = etree.SubElement(TagExportacion,cex+"NombreExportador",{})
                    TagNombreExportador.text = str(factura.company_id.name)
                    TagCodigoExportador = etree.SubElement(TagExportacion,cex+"CodigoExportador",{})
                    TagCodigoExportador.text = factura.company_id.fel_codigo_exportador if factura.company_id.fel_codigo_exportador else "N/A"



                if tipo == 'NCRE':
                    factura_original_id = self.env['account.invoice'].search([('number','=',factura.origin)])
                    if factura_original_id and factura.currency_id.id == factura_original_id.currency_id.id:
                        logging.warn('si')
                        TagComplementos = etree.SubElement(TagDatosEmision,DTE_NS+"Complementos",{})
                        cno = "{http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0}"
                        NSMAP_REF = {"cno": "http://www.sat.gob.gt/face2/ComplementoReferenciaNota/0.1.0"}
                        datos_complemento = {'IDComplemento': 'Notas', 'NombreComplemento':'Notas','URIComplemento':'text'}
                        TagComplemento = etree.SubElement(TagComplementos,DTE_NS+"Complemento",datos_complemento)
                        datos_referencias = {
                            'FechaEmisionDocumentoOrigen': str(factura_original_id.invoice_date),
                            'MotivoAjuste': 'Nota de credito factura',
                            'NumeroAutorizacionDocumentoOrigen': str(factura_original_id.fel_numero_autorizacion),
                            'NumeroDocumentoOrigen': str(factura_original_id.fel_numero),
                            'SerieDocumentoOrigen': str(factura_original_id.fel_serie),
                            'Version': '0.0'
                        }
                        TagReferenciasNota = etree.SubElement(TagComplemento,cno+"ReferenciasNota",datos_referencias,nsmap=NSMAP_REF)

                if factura.currency_id.id != factura.company_id.currency_id.id:
                    TagAdenda = etree.SubElement(TagSAT,DTE_NS+"Adenda",{})
                    if factura.comment:
                        TagComentario = etree.SubElement(TagAdenda, DTE_NS+"Comentario",{})
                        TagComentario.text = factura.comment
                    if factura.currency_id.id != factura.company_id.currency_id.id:
                        TagNitCliente = etree.SubElement(TagAdenda, DTE_NS+"NitCliente",{})
                        if factura.partner_id.vat:
                            if '-' in factura.partner_id.vat:
                                TagNitCliente.text = factura.partner_id.vat.replace('-','')
                            else:
                                TagNitCliente.text = factura.partner_id.vat
                # if factura.narration:
                #     TagAdenda = etree.SubElement(TagDTE, DTE_NS+"Adenda",{})
                #     TagDECER = etree.SubElement(TagAdenda,"DECertificador",{})
                #     TagDECER.text = str(factura.narration)

                # if factura.narration:
                #     TagAdenda = etree.SubElement(TagSAT,DTE_NS+"Adenda",{})
                #     TagComentario = etree.SubElement(TagAdenda, DTE_NS+"Comentario",{})
                #     TagComentario.text = factura.narration

                xmls = etree.tostring(GTDocumento, encoding="UTF-8")
                xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls)


                url = "https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml"

                nit_company = "CF"
                if '-' in factura.company_id.vat:
                    nit_company = factura.company_id.vat.replace('-','')
                else:
                    nit_company = factura.company_id.vat


                nuevo_json = {
                    'llave': str(factura.company_id.fel_llave_pre_firma),
                    'codigo': str(nit_company),
                    'alias': str(factura.company_id.fel_usuario),
                    'es_anulacion': 'N',
                    'archivo': xmls_base64.decode("utf-8")
                }

                nuevos_headers = {"content-type": "application/json"}
                response = requests.post(url, json = nuevo_json, headers = nuevos_headers)

                respone_json=response.json()
                logging.warn(respone_json)

                if respone_json['resultado']:
                        headers = {
                            "USUARIO": str(factura.company_id.fel_usuario),
                            "LLAVE": str(factura.company_id.fel_llave_firma),
                            "IDENTIFICADOR": str(factura.journal_id.name)+'/'+str(factura.payment_reference) if factura.payment_reference else str(factura.journal_id.name)+'/'+str(factura.id),
                            "Content-Type": "application/json",
                        }

                        nit_company = "CF"
                        if '-' in factura.company_id.vat:
                            nit_company = factura.company_id.vat.replace('-','')
                        else:
                            nit_company = factura.company_id.vat
                        data = {
                            "nit_emisor": str(nit_company),
                            "correo_copia": str(factura.company_id.email),
                            "xml_dte": respone_json["archivo"]
                        }

                        r = requests.post("https://certificador.feel.com.gt/fel/certificacion/v2/dte/", json=data, headers=headers)
                        retorno_certificacion_json = r.json()
                        logging.warn(retorno_certificacion_json)
                        if retorno_certificacion_json['resultado']:
                            factura.fel_numero_autorizacion = retorno_certificacion_json["uuid"]
                            # factura.name = str(retorno_certificacion_json["serie"])+"/"+str(retorno_certificacion_json["numero"])
                            factura.fel_serie = retorno_certificacion_json["serie"]
                            factura.fel_numero = retorno_certificacion_json["numero"]
                            factura.fel_documento_certificado = "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="+retorno_certificacion_json["uuid"]
                        else:
                            raise UserError(str(retorno_certificacion_json))
                else:
                    raise UserError(str(respone_json))

        return super(AccountMove, self)._post()


    def button_draft(self):
        for factura in self:
            if factura.fel_serie and factura.fel_numero and factura.fel_numero_autorizacion and factura.company_id.fel_llave_firma:
                attr_qname = etree.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
                DTE_NS = "{http://www.sat.gob.gt/dte/fel/0.1.0}"
                # Nuevo SMAP
                NSMAP = {
                    "ds": "http://www.w3.org/2000/09/xmldsig#",
                    "dte": "http://www.sat.gob.gt/dte/fel/0.1.0",
                    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
                }
                tipo = factura.journal_id.fel_tipo_dte
                GTAnulacionDocumento = etree.Element(DTE_NS+"GTAnulacionDocumento", {attr_qname: 'http://www.sat.gob.gt/dte/fel/0.1.0'}, Version="0.1", nsmap=NSMAP)
                datos_sat = {'ClaseDocumento': 'dte'}
                TagSAT = etree.SubElement(GTAnulacionDocumento,DTE_NS+"SAT",{})
                # dato_anulacion = {'ID': 'DatosCertificados'}
                dato_anulacion = {"ID": "DatosCertificados"}
                TagAnulacionDTE = etree.SubElement(TagSAT,DTE_NS+"AnulacionDTE",dato_anulacion)
                fecha_factura = self.fecha_hora_factura(factura.invoice_date)
                fecha_anulacion = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%Y-%m-%d")
                hora_anulacion = datetime.datetime.strftime(fields.Datetime.context_timestamp(self, datetime.datetime.now()), "%H:%M:%S")
                fecha_anulacion = str(fecha_anulacion)+'T'+str(hora_anulacion)
                nit_partner = "CF"
                if factura.partner_id.vat:
                    logging.warn('si nit')
                    if ('-' in factura.partner_id.vat):
                        logging.warn('si nit if')
                        nit_partner = factura.partner_id.vat.replace('-','')
                    else:
                        nit_partner = factura.partner_id.vat
                        logging.warn('si nit else')


                nit_company = "CF"
                if factura.journal_id.direccion_id.vat and ('-' in factura.journal_id.direccion_id.vat):
                    nit_company = factura.company_id.vat.replace('-','')
                else:
                    nit_company = factura.company_id.vat

                datos_generales = {
                    "ID": "DatosAnulacion",
                    "NumeroDocumentoAAnular": str(factura.fel_numero_autorizacion),
                    "NITEmisor": str(nit_company),
                    "IDReceptor": str(nit_partner),
                    "FechaEmisionDocumentoAnular": fecha_factura,
                    "FechaHoraAnulacion": fecha_anulacion,
                    "MotivoAnulacion": "Anulacion factura"
                }
                if tipo == 'FACT' and (factura.currency_id.id !=  factura.company_id.currency_id.id):
                    datos_generales['IDReceptor'] = "CF"
                TagDatosGenerales = etree.SubElement(TagAnulacionDTE,DTE_NS+"DatosGenerales",datos_generales)


                xmls = etree.tostring(GTAnulacionDocumento, encoding="UTF-8")
                logging.warn('xmls')
                logging.warn(xmls)
                xmls = xmls.decode("utf-8").replace("&amp;", "&").encode("utf-8")
                xmls_base64 = base64.b64encode(xmls)
                logging.warn(xmls_base64)
                logging.warn('BASE 64')
                logging.warn(xmls_base64.decode("utf-8"))


                url = "https://signer-emisores.feel.com.gt/sign_solicitud_firmas/firma_xml"

                nuevo_json = {
                    "llave": factura.company_id.fel_llave_pre_firma,
                    "archivo": xmls_base64.decode("utf-8"),
                    "codigo": str(factura.company_id.vat),
                    "alias": str(factura.company_id.fel_usuario),
                    "es_anulacion": "S"
                }
                logging.warn('NUEVO JSON ARCHIVO')
                logging.warn(xmls_base64.decode("utf-8"))

                nuevos_headers = {"content-type": "application/json"}
                response = requests.post(url, json = nuevo_json, headers = nuevos_headers)
                respone_json=response.json()
                logging.warn('RESPONSE JSON')
                logging.warn(respone_json)
                if respone_json['resultado']:


                    headers = {
                        "USUARIO": str(factura.company_id.fel_usuario),
                        "LLAVE": factura.company_id.fel_llave_firma,
                        "IDENTIFICADOR": str(factura.journal_id.name)+'/'+str(factura.id)+'/'+'ANULACION',
                        "Content-Type": "application/json",
                    }
                    data = {
                        "nit_emisor": factura.company_id.vat,
                        "correo_copia": factura.company_id.email,
                        "xml_dte": respone_json["archivo"]
                    }

                    r = requests.post("https://certificador.feel.com.gt/fel/anulacion/v2/dte/", json=data, headers=headers)
                    logging.warn(r.json())
                    retorno_certificacion_json = r.json()
                    logging.warn('si anuló')
                    if not retorno_certificacion_json['resultado']:
                        raise UserError(str('ERROR AL ANULAR'))
                else:
                    raise UserError(str('ERROR AL ANULAR'))

        return super(AccountMove, self).button_draft()
